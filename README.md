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

---

## 🛠 Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — framework web assíncrono
- **[yfinance](https://github.com/ranaroussi/yfinance)** — dados do Yahoo Finance
- **[SQLAlchemy](https://www.sqlalchemy.org/) + PostgreSQL** — persistência de usuários e watchlist
- **[Redis](https://redis.io/)** — cache de respostas
- **[PyJWT](https://pyjwt.readthedocs.io/) + Passlib/bcrypt** — autenticação segura
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
├── services/
│   └── asset_service.py     # Lógica de negócio + cache read-through
├── infrastructure/
│   ├── providers.py         # IAssetProvider / YahooFinanceProvider
│   ├── cache.py             # ICacheProvider / RedisCache
│   └── database.py          # Engine SQLAlchemy + get_db()
├── models/
│   ├── user.py              # ORM User/Watchlist + schemas Pydantic
│   └── asset.py             # Schemas Pydantic de ativos
├── core/
│   ├── config.py            # Variáveis de ambiente
│   └── security.py          # JWT, bcrypt, get_current_user()
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

### 3. Subir com Docker (recomendado)
```bash
docker compose up --build
```
> Certifique-se de que a porta **6379** (Redis) e **8000** (API) estão livres.

### 4. Acessar a documentação interativa
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
