# 📘 Documentação da API Financeira (Asset Service)

Esta API fornece dados em tempo real sobre o mercado financeiro, incluindo ações da B3 (Brasil), Cryptomoedas e Stocks Americanas, utilizando o **Yahoo Finance** como provedor principal.

---

## 🚀 Informações Gerais

* **Ticker Auto-Formatting**: A API identifica automaticamente o mercado:
    * `PETR4` → Vira `PETR4.SA` (B3)
    * `BTC` → Vira `BTC-USD` (Crypto)
    * `AAPL` → Mantém `AAPL` (Nasdaq/NYSE)
* **Base URL**: `http://localhost/assets`

---

## 🛠 Endpoints Disponíveis

### 1. Obter Cotação Atual
**Endpoint:** `GET /assets/{ticker}/quote`  
**Descrição:** Retorna o preço atual, nome da empresa, logo e a tendência do ativo. Ideal para os "cards" de Watchlist.

| Campo | Descrição | Exemplo |
| :--- | :--- | :--- |
| `price_usd` | Valor atual (BRL ou USD conforme o ativo) | `34.50` |
| `direction` | Status visual: `subindo`, `caindo` ou `estável` | `"subindo"` |
| `icon_url` | Link para o logo da empresa | `"https://logo.clearbit.com/petrobras.com"` |

### 2. Histórico de Preços (Gráfico)
**Endpoint:** `GET /assets/{ticker}/history?period=1mo&interval=1d`  
**Descrição:** Dados históricos para alimentar gráficos de linha ou velas (candlestick).

* **Parâmetros de Período (`period`):** `1d`, `5d`, `1mo`, `6mo`, `1y`, `max`.
* **Parâmetros de Intervalo (`interval`):** `1m`, `5m`, `1h`, `1d`, `1wk`.

### 3. Notícias Relacionadas
**Endpoint:** `GET /assets/{ticker}/news`  
**Descrição:** Notícias recentes que impactam o preço do ativo.

> **Nota Técnica:** O campo `summary` (resumo) é extraído de forma inteligente, buscando na descrição caso o resumo principal esteja vazio.

| Campo | Descrição |
| :--- | :--- |
| `title` | Título da matéria |
| `summary` | Breve resumo para visualização prévia |
| `publisher` | Veículo que publicou (Ex: Bloomberg, Yahoo) |
| `provider_publish_time` | Data de publicação no formato ISO |

### 4. Saúde Financeira e Indicadores
**Endpoint:** `GET /assets/{ticker}/financials`  
**Descrição:** Análise fundamentalista rápida.
* **Market Cap:** Valor de mercado da empresa.
* **P/E Ratio:** Preço sobre Lucro.
* **Recommendation:** Sugestão dos analistas (`buy`, `hold`, `strong_buy`).

### 5. Dividendos
**Endpoint:** `GET /assets/{ticker}/dividends`  
**Descrição:** Lista os últimos 10 pagamentos de proventos registrados.

### 6. Busca Global
**Endpoint:** `GET /assets/search?query={texto}`  
**Descrição:** Implementação de busca para sugestões de tickers (Ex: digitar "MGLU" e sugerir "MGLU3.SA").

---

## ⚠️ Tratamento de Erros

A API utiliza códigos HTTP padrão:
* `200`: Sucesso.
* `404`: Ativo não encontrado.
* `500`: Erro interno ou falha de conexão com provedor.

## 🚀 Como Rodar o Projeto

Este projeto utiliza o [uv](https://github.com/astral-sh/uv), um gerenciador de pacotes Python extremamente rápido.

### Pré-requisitos
- Ter o `uv` instalado (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Ter o `docker` instalado (`curl -fsSL https://get.docker.com -o get-docker.sh` e `sudo sh get-docker.sh`)

### Passo a Passo
1. **Clonar o repositório:**
   ```bash
   git clone <url-do-repositorio>
   cd <nome-do-projeto>
   docker compose up --build
   
Obs: Verifique se a porta: 6379 está livre !