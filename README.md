# 🚀 Easy Investment — Backend API

API RESTful de dados financeiros em tempo real, construída com **FastAPI** e **Python**. Fornece cotações, histórico, notícias, dividendos e indicadores fundamentalistas de ações da B3, criptomoedas e stocks americanas — com autenticação JWT e cache Redis integrado.

---

## ✨ Funcionalidades

| Recurso | Descrição |
|---|---|
| 📈 **Cotação em tempo real** | Preço atual, tendência (subindo/caindo/estável) e logo do ativo |
| 📊 **Histórico de preços** | Dados OHLC para gráficos de linha ou candlestick |
| 📰 **Notícias** | Últimas notícias relacionadas ao ativo com resumo e fonte |
| 💰 **Dividendos** | Histórico dos últimos proventos pagos |
| 🏦 **Indicadores fundamentalistas** | Market Cap, P/E Ratio, Dividend Yield, recomendação de analistas |
| 🔍 **Busca global** | Autocompletar de tickers (ex: digitar "MGLU" sugere "MGLU3.SA") |
| 🔐 **Autenticação JWT** | Registro, login e proteção de rotas com Bearer Token |
| ⚡ **Cache Redis** | TTL configurável por endpoint para minimizar chamadas à API externa |
| 🤖 **Agente de IA** | Chat especializado em gestão de ativos, com histórico por usuário, watchlist no contexto e base de conhecimento RAG |

---

## 🛠 Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — framework web assíncrono
- **[yfinance](https://github.com/ranaroussi/yfinance)** — dados do Yahoo Finance
- **[SQLAlchemy](https://www.sqlalchemy.org/) + PostgreSQL** — persistência de usuários e watchlist
- **[Redis](https://redis.io/)** — cache de respostas
- **[PyJWT](https://pyjwt.readthedocs.io/) + Passlib/bcrypt** — autenticação segura
- **[Agno](https://docs.agno.com/)** — framework do agente de IA (sessões, memória, tools, RAG)
- **[Gemini](https://ai.google.dev/) + [Groq](https://console.groq.com/)** — modelos de linguagem, com fallback automático
- **[pgvector](https://github.com/pgvector/pgvector)** — busca vetorial da base de conhecimento
- **[uv](https://github.com/astral-sh/uv)** — gerenciador de pacotes ultrarrápido
- **Docker + Docker Compose** — orquestração do ambiente completo

---

## 🗂 Estrutura do Projeto

```
├── main.py                  # Entry point — registra routers e middlewares
├── api/                     # Camada HTTP (routers FastAPI)
│   ├── asset_router.py      # Endpoints de ativos (protegidos por JWT)
│   ├── auth_router.py       # Login e geração de token
│   ├── user_router.py       # CRUD de usuários
│   └── profile_router.py    # Perfil e watchlist do usuário
│   └── ai_router.py         # Endpoints do agente de IA
├── services/
│   ├── asset_service.py     # Lógica de negócio + cache read-through
│   └── ai/
│       ├── chat_service.py  # Orquestra runs, streaming e sessões
│       ├── agent_factory.py # Monta o Agent do Agno por conversa
│       ├── tools.py         # Tools de mercado e de watchlist
│       ├── prompts.py       # Identidade e regras do agente
│       └── context.py       # Retrato do usuário (sem ORM vazando)
├── infrastructure/
│   ├── providers.py         # IAssetProvider / YahooFinanceProvider
│   ├── cache.py             # ICacheProvider / RedisCache
│   ├── database.py          # Engine SQLAlchemy + get_db()
│   └── ai/
│       ├── runtime.py       # Objetos caros do agente (criados no lifespan)
│       ├── agent_db.py      # Banco do Agno (sessões e resumos)
│       ├── knowledge.py     # Knowledge + PgVector + embedder Gemini
│       └── model_router.py  # Fallback Gemini -> Groq
├── models/
│   ├── user.py              # ORM User/Watchlist + schemas Pydantic
│   ├── asset.py             # Schemas Pydantic de ativos
│   └── ai.py                # Schemas do chat e das sessões
├── core/
│   ├── config.py            # Variáveis de ambiente
│   └── security.py          # JWT, bcrypt, get_current_user()
├── knowledge_docs/          # Base de conhecimento curada (11 documentos)
├── scripts/
│   └── ingest_knowledge.py  # Ingestão da base no pgvector
├── tests/
├── docker-compose.yaml
└── Dockerfile
```

---

## ⚙️ Como Rodar

### Pré-requisitos
- [Docker](https://docs.docker.com/get-docker/) e Docker Compose
- [uv](https://github.com/astral-sh/uv) (apenas para desenvolvimento local)

### 1. Clonar o repositório
```bash
git clone https://github.com/fenilonilo/easy_investment_back.git
cd easy_investment_back
```

### 2. Configurar variáveis de ambiente
```bash
cp .env.example .env
```
Edite o `.env` e defina uma `SECRET_KEY` segura:
```env
SECRET_KEY=troque_por_uma_chave_forte_e_aleatoria
ALGORITHM=HS256
REDIS_URL=redis://redis_cache:6379
CACHE_TTL_SECONDS=60
```

Para habilitar o agente de IA, adicione também as chaves dos modelos (veja a
seção [Agente de IA](#-agente-de-ia)):
```env
GOOGLE_API_KEY=sua_chave_do_google_ai_studio
GROQ_API_KEY=sua_chave_da_groq
```

### 3. Subir com Docker (recomendado)
```bash
docker compose up --build
```
> Certifique-se de que as portas **6379** (Redis), **5433** (Postgres do agente)
> e **8000** (API) estão livres.

### 4. Carregar a base de conhecimento do agente
```bash
uv run python scripts/ingest_knowledge.py
```
Roda uma vez só. É idempotente — rodar de novo pula o que já foi ingerido.

### 5. Acessar a documentação interativa
Abra no navegador: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔌 Endpoints Principais

> Todos os endpoints de `/assets` exigem autenticação. Envie o header:
> `Authorization: Bearer <token>`

### Autenticação
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/auth/login` | Login — retorna JWT |
| `POST` | `/users/` | Criar novo usuário |

### Ativos
| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/assets?search=PETR` | Busca global de tickers |
| `GET` | `/assets/{ticker}` | Cotação atual do ativo |
| `GET` | `/assets/{ticker}/history?period=1mo` | Histórico de preços |
| `GET` | `/assets/{ticker}/news` | Notícias relacionadas |
| `GET` | `/assets/{ticker}/dividends` | Histórico de dividendos |
| `GET` | `/assets/{ticker}/financials` | Indicadores fundamentalistas |

### Parâmetros de período para `/history`
`1d` · `5d` · `1mo` · `6mo` · `1y` · `max`

---

## 🤖 Agente de IA

Chat especializado em **gestão e avaliação de ativos financeiros**, construído com o
framework [Agno](https://docs.agno.com/). Cada usuário tem as próprias conversas,
e o agente já recebe a watchlist e o perfil de investidor no contexto — não precisa
perguntar quais ativos você acompanha.

### O que ele faz

- **Consulta dados reais de mercado** via `YFinanceTools` e via o `AssetService` da
  própria API (aproveitando o cache Redis já existente). Nunca inventa cotação.
- **Explica métricas** a partir de uma base de conhecimento RAG em português:
  ROI, ROE, ROIC, P/L, P/VP, EV/EBITDA, Dividend Yield, valuation por DCF e
  múltiplos, endividamento, risco e análise técnica.
- **Mantém histórico por conversa**, com resumo automático das mensagens antigas
  para não estourar o contexto do modelo.
- **Altera a watchlist** quando você pede ("adiciona PETR4 na minha lista").
- **Adapta a resposta ao perfil** — `CONSERVATIVE`, `MODERATE` ou `AGGRESSIVE`.

### Endpoints

> Todos exigem `Authorization: Bearer <token>`.

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/ai/chat` | Envia mensagem e recebe a resposta completa em JSON |
| `POST` | `/ai/chat/stream` | Mesma conversa via SSE (streaming de tokens) |
| `GET` | `/ai/sessions` | Lista as conversas do usuário |
| `GET` | `/ai/sessions/{id}` | Histórico completo de mensagens |
| `GET` | `/ai/sessions/{id}/summary` | Resumo gerado da conversa |
| `DELETE` | `/ai/sessions/{id}` | Apaga a conversa |

Omita `session_id` no `/ai/chat` para começar uma conversa nova — o id criado volta
na resposta. Sessão de outro usuário sempre responde **404**.

**Exemplo:**
```bash
curl -X POST http://localhost:8000/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "o P/L da PETR4 está caro comparado com a minha watchlist?"}'
```

**Streaming** (eventos `start`, `token`, `tool`, `done`, `error`):
```bash
curl -N -X POST http://localhost:8000/ai/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "explique ROIC", "session_id": "..."}'
```

### Modelos e fallback

O **Gemini** é o modelo principal. Quando ele estoura cota ou fica indisponível
(429, 503, timeout), a requisição é repetida automaticamente na **Groq** e o Gemini
entra em quarentena por 5 minutos — nesse período todas as chamadas vão direto para
a Groq, sem tentar o Gemini de novo. A flag de quarentena vive no Redis.

Erro de credencial (chave inválida, 401/403) **não** dispara fallback: ele sobe como
`502` para você ver o problema, em vez de ser mascarado.

O campo `provider` na resposta diz qual modelo respondeu.

### Base de conhecimento

Fica em `knowledge_docs/` — 11 documentos curados em português, versionados no git,
com fórmula, interpretação, faixas típicas e armadilhas de cada métrica. A ingestão
carrega também algumas páginas públicas da CVM e da B3.

```bash
uv run python scripts/ingest_knowledge.py            # ingere o que falta
uv run python scripts/ingest_knowledge.py --force    # reprocessa tudo
uv run python scripts/ingest_knowledge.py --listar   # o que já está lá
```

Os vetores ficam no serviço `postgres_ai` (imagem `pgvector/pgvector`), separado do
banco `easy_finace` da aplicação. O Agno cria e gerencia as próprias tabelas lá —
não é preciso rodar migração.

> Se a base de conhecimento estiver indisponível, o agente continua respondendo
> com as tools de mercado e o histórico, apenas sem o RAG.

### Variáveis de ambiente

| Variável | Padrão | Para que serve |
|---|---|---|
| `GOOGLE_API_KEY` | — | Chave do [Google AI Studio](https://aistudio.google.com/apikey). Usada pelo modelo principal e pelos embeddings |
| `GROQ_API_KEY` | — | Chave da [Groq](https://console.groq.com/keys). Modelo de fallback |
| `AI_DATABASE_URL` | `postgresql+psycopg://agno:agno@postgres_ai:5432/agno_ai` | Postgres com pgvector |
| `GEMINI_MODEL_ID` | `gemini-3.5-flash` | Modelo principal |
| `GROQ_MODEL_ID` | `openai/gpt-oss-120b` | Modelo de fallback |
| `GROQ_REASONING_EFFORT` | `medium` | Esforço de raciocínio na Groq |
| `GEMINI_EMBEDDER_ID` | `gemini-embedding-001` | Modelo de embeddings |
| `GEMINI_EMBEDDER_DIMENSIONS` | `1536` | Dimensão dos vetores |
| `AI_HISTORY_RUNS` | `5` | Quantas interações anteriores entram no contexto |
| `AI_FALLBACK_COOLDOWN_SECONDS` | `300` | Duração da quarentena do Gemini |

---

## 🔍 Logs e diagnóstico

Cada requisição recebe um **`request_id`** curto que aparece em toda linha de log dela,
no header `X-Request-ID` da resposta e nos corpos de erro. É ele que liga
"o app mostrou erro" ao traceback exato no servidor.

```
2026-08-14 01:10:40 | INFO    | ai.chat_service | req=187ee84dc121 | stream iniciado | user=50c0b032… session=0f9c2a7e… provider=gemini | msg=o que é ROE?
2026-08-14 01:10:41 | INFO    | ai.chat_service | req=187ee84dc121 | tool cotacao_atual(PETR4) ok em 412ms | 284 chars
2026-08-14 01:10:44 | INFO    | ai.chat_service | req=187ee84dc121 | stream concluído | provider=gemini em 3821ms | 1204 chars | tools=['cotacao_atual']
```

Para achar tudo de uma falha que o usuário reportou:

```bash
docker compose logs api_financeira | grep 187ee84dc121
```

### O que cada aviso significa

| Mensagem no log | O que fazer |
|---|---|
| `Knowledge base VAZIA (0 documentos)` | Rode `uv run python scripts/ingest_knowledge.py`. É a causa do `Found 0 documents` do agno |
| `Knowledge base indisponível` | `postgres_ai` fora do ar — `docker compose ps` |
| `Gemini indisponível, caindo para a Groq` | Normal: cota estourada, o fallback funcionou |
| `Gemini falhou por erro NÃO transitório` | Chave inválida ou requisição malformada; trocar de modelo não resolveria |
| `nenhum token gerado pelo modelo` | O provider devolveu resposta vazia — geralmente filtro de segurança |
| `tool X FALHOU` | A ferramenta quebrou; o agente segue sem aquele dado |
| `Nenhuma chave de IA configurada` | Falta `GOOGLE_API_KEY` / `GROQ_API_KEY` no `.env` |

### Variáveis

| Variável | Padrão | Para que serve |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Nível do código da aplicação. `DEBUG` mostra as decisões internas |
| `LOG_FORMAT` | `text` | `text` para terminal, `json` para agregador |
| `LOG_LEVEL_LIBS` | `WARNING` | Nível de agno/httpx/yfinance. Em `INFO` o agno afoga o log |
| `LOG_MESSAGE_PREVIEW_CHARS` | `120` | Trecho da mensagem gravado. `0` grava só o tamanho |

---

## 🧪 Testes

```bash
uv run pytest
```

Cobrem a lógica que não depende de rede: fallback entre modelos, isolamento de
sessões entre usuários, escopo das tools de escrita e tradução dos eventos de
streaming. Nenhum teste chama LLM de verdade.

---

## 🌍 Mercados Suportados

A API detecta automaticamente o mercado pelo formato do ticker:

| Exemplo | Resultado | Mercado |
|---|---|---|
| `PETR4` | `PETR4.SA` | B3 (Brasil) |
| `BTC` | `BTC-USD` | Criptomoeda |
| `AAPL` | `AAPL` | Nasdaq/NYSE (EUA) |

---

## 🔒 Segurança

- Senhas armazenadas com hash **bcrypt**
- Tokens JWT com expiração de **1 hora**
- Arquivo `.env` protegido pelo `.gitignore` — nunca suba credenciais reais

---

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
