"""Ingestão do knowledge base do agente financeiro.

Carrega os documentos curados de `knowledge_docs/` e um conjunto de páginas
públicas para o pgvector. Idempotente: por padrão pula o que já foi ingerido.

    uv run python scripts/ingest_knowledge.py            # ingere o que falta
    uv run python scripts/ingest_knowledge.py --force    # reprocessa tudo
    uv run python scripts/ingest_knowledge.py --somente-docs
    uv run python scripts/ingest_knowledge.py --listar   # o que já está lá

Requisitos: `postgres_ai` no ar (docker compose up postgres_ai) e
`GOOGLE_API_KEY` definida — a ingestão gera embeddings pelo Gemini.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import httpx

# Permite rodar como `python scripts/ingest_knowledge.py` a partir da raiz.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import GOOGLE_API_KEY  # noqa: E402
from infrastructure.ai.agent_db import build_agent_db  # noqa: E402
from infrastructure.ai.knowledge import build_knowledge  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("ingest")

DOCS_DIR = Path(__file__).resolve().parent.parent / "knowledge_docs"

# Páginas públicas complementares aos documentos curados.
#
# A lista é curta de propósito: cada URL abaixo foi verificada e devolve HTML
# com conteúdo de verdade. Fontes descartadas na verificação, e por quê:
#   - Investopedia: responde 403 a cliente automatizado, mas com ~680 KB de
#     corpo (página de bloqueio). Sem checar o status, essa página entraria no
#     knowledge base como se fosse conteúdo — pior que não ter a fonte.
#   - bcb.gov.br/controleinflacao/*: SPA em Angular; o HTML tem ~2,8 KB de
#     shell e nenhum texto útil.
URLS_PUBLICAS = [
    (
        "CVM — Portal do Investidor",
        "https://www.gov.br/investidor/pt-br",
    ),
    (
        "CVM — Publicações educacionais",
        "https://www.gov.br/investidor/pt-br/educacional/publicacoes-educacionais",
    ),
    (
        "B3 — Ações",
        "https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/acoes.htm",
    ),
    (
        "B3 — Fundos de Investimento Imobiliário (FII)",
        "https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/fundos-de-investimento-imobiliario-fii.htm",
    ),
]

# Abaixo disso o retorno quase sempre é página de erro, bloqueio ou shell de SPA.
TAMANHO_MINIMO_HTML = 8_000


async def ingerir_docs(knowledge, force: bool) -> tuple[int, int]:
    arquivos = sorted(DOCS_DIR.glob("*.md"))
    if not arquivos:
        logger.error("Nenhum .md encontrado em %s", DOCS_DIR)
        return 0, 0

    ok = falhas = 0
    for arquivo in arquivos:
        titulo = arquivo.stem
        try:
            await knowledge.add_content_async(
                name=titulo,
                path=str(arquivo),
                metadata={"fonte": "curado", "idioma": "pt-BR", "arquivo": arquivo.name},
                skip_if_exists=not force,
                upsert=True,
            )
            logger.info("doc  OK    %s", arquivo.name)
            ok += 1
        except Exception as exc:
            logger.warning("doc  FALHA %s — %s", arquivo.name, exc)
            falhas += 1
    return ok, falhas


async def url_serve(client: httpx.AsyncClient, url: str) -> tuple[bool, str]:
    """Pré-checagem antes de entregar a URL ao reader do Agno.

    Existe porque um 403 pode vir acompanhado de centenas de KB de página de
    bloqueio: sem olhar o status, isso viraria "conhecimento" no banco vetorial.
    """
    try:
        resposta = await client.get(url)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

    if resposta.status_code != 200:
        return False, f"HTTP {resposta.status_code}"
    if len(resposta.content) < TAMANHO_MINIMO_HTML:
        return False, f"corpo muito pequeno ({len(resposta.content)} bytes)"
    return True, ""


async def ingerir_urls(knowledge, force: bool) -> tuple[int, int]:
    ok = falhas = 0
    headers = {"User-Agent": "Mozilla/5.0 (compatible; API-Financeira-Ingest/1.0)"}
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=30, headers=headers
    ) as client:
        for titulo, url in URLS_PUBLICAS:
            serve, motivo = await url_serve(client, url)
            if not serve:
                logger.warning("url  PULADA %s — %s", titulo, motivo)
                falhas += 1
                continue
            try:
                await knowledge.add_content_async(
                    name=titulo,
                    url=url,
                    metadata={"fonte": "web", "url": url},
                    skip_if_exists=not force,
                    upsert=True,
                )
                logger.info("url  OK    %s", titulo)
                ok += 1
            except Exception as exc:
                # Esperado de vez em quando: robots, mudança de layout, timeout.
                logger.warning("url  PULADA %s — %s", titulo, exc)
                falhas += 1
    return ok, falhas


async def listar(knowledge) -> None:
    conteudos, total = await knowledge.aget_content(limit=200, page=1)
    logger.info("%s conteúdo(s) no knowledge base:", total)
    for item in conteudos or []:
        nome = getattr(item, "name", None) or (
            item.get("name") if isinstance(item, dict) else "?"
        )
        status = getattr(item, "status", None) or (
            item.get("status") if isinstance(item, dict) else ""
        )
        logger.info("  - %s (%s)", nome, status)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="reprocessa o que já existe")
    parser.add_argument("--somente-docs", action="store_true", help="ignora as URLs")
    parser.add_argument("--listar", action="store_true", help="só lista o que já foi ingerido")
    args = parser.parse_args()

    if not GOOGLE_API_KEY:
        logger.error(
            "GOOGLE_API_KEY não definida. A ingestão gera embeddings pelo Gemini e "
            "não tem como rodar sem ela."
        )
        return 1

    db = build_agent_db()
    # Bloqueante de propósito: conecta no Postgres e cria o schema se faltar.
    knowledge = await asyncio.to_thread(build_knowledge, db)

    if args.listar:
        await listar(knowledge)
        return 0

    docs_ok, docs_falha = await ingerir_docs(knowledge, args.force)
    urls_ok = urls_falha = 0
    if not args.somente_docs:
        urls_ok, urls_falha = await ingerir_urls(knowledge, args.force)

    logger.info("-" * 60)
    logger.info("documentos: %s ingeridos, %s com falha", docs_ok, docs_falha)
    logger.info("urls:       %s ingeridas, %s puladas", urls_ok, urls_falha)

    # Documento curado falhando é problema de verdade; URL pulada não é.
    return 1 if docs_falha else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
