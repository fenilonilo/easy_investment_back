FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 1. Copiamos APENAS os arquivos de configuração primeiro
COPY pyproject.toml uv.lock ./

# 2. Instalamos EXATAMENTE as versões travadas no uv.lock (sem dev)
# O comando '--system' instala no Python do container
RUN uv export --frozen --no-dev --no-hashes --no-emit-project | uv pip install --system --no-cache -r -

# 3. Agora copiamos o resto do código (api, services, etc)
# Como as dependências já foram instaladas na camada acima,
# mudar o código não dispara uma nova instalação.
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]