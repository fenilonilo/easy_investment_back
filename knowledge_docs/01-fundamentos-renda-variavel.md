# Fundamentos: classes de ativos

## Renda fixa x renda variável

**Renda fixa**: você empresta dinheiro e conhece a regra de remuneração no momento da aplicação (não necessariamente o valor final). Tesouro Direto, CDB, LCI/LCA, debêntures, CRI/CRA.

**Renda variável**: você vira sócio ou dono de um ativo cujo preço oscila livremente. Não há promessa de retorno. Ações, ETFs, FIIs, BDRs, criptomoedas.

A confusão mais comum: "renda fixa não perde dinheiro". Perde. Um título prefixado marcado a mercado cai quando os juros sobem — é o efeito da **marcação a mercado**. Só quem carrega até o vencimento trava o retorno contratado.

## Ações

Fração do capital social de uma empresa. Quem tem ação é sócio: participa dos lucros (dividendos, JCP) e do risco.

Na B3 o ticker segue o padrão `LLLLN`:

| Sufixo | Tipo | O que é |
|---|---|---|
| 3 | ON (ordinária) | Dá direito a voto. Ex.: `PETR3`, `VALE3` |
| 4 | PN (preferencial) | Sem voto (em geral), com preferência no recebimento de proventos. Ex.: `PETR4`, `ITUB4` |
| 5, 6, 7, 8 | PN classes A/B/... | Preferenciais com regras específicas de estatuto. Ex.: `BRDT6` |
| 11 | Unit / ETF / BDR | Pacote de ações (`SANB11`), cota de ETF (`BOVA11`) ou BDR (`ROXO34` é 34) |

**Tag along**: percentual do valor pago ao controlador que o minoritário recebe se a empresa for vendida. Ações ON do Novo Mercado têm 100%. PNs muitas vezes têm 80% ou nada — é um risco real, não detalhe burocrático.

## ETFs

Fundos negociados em bolsa que replicam um índice. Você compra uma cota e leva a cesta inteira.

- `BOVA11` — Ibovespa
- `SMAL11` — small caps
- `IVVB11` — S&P 500 em reais
- `HASH11` — cesta de criptomoedas

Vantagem: diversificação instantânea com uma ordem. Desvantagem: você não escolhe a composição, e paga taxa de administração (geralmente 0,1% a 0,7% a.a.).

**ETF de ação no Brasil não distribui dividendos**: os proventos são reinvestidos no próprio fundo, o que aparece como valorização da cota, não como dinheiro na conta.

## FIIs (Fundos de Investimento Imobiliário)

Fundos que investem em imóveis ou em papéis lastreados em imóveis. Ticker termina em 11 (`HGLG11`, `MXRF11`).

Duas famílias:

- **Tijolo**: donos de imóveis físicos (galpões, shoppings, lajes). A receita é aluguel. Riscos: vacância, inadimplência, obsolescência do imóvel.
- **Papel**: carteira de CRIs (recebíveis imobiliários). A receita é juros. Riscos: crédito e indexador (IPCA ou CDI).

Métrica central: **P/VP** (preço sobre valor patrimonial). Abaixo de 1 o mercado está pagando menos que o valor contábil dos ativos — pode ser oportunidade ou sinal de que o patrimônio está superavaliado no papel.

Obrigação legal: distribuir no mínimo 95% do lucro semestral apurado pelo regime de caixa. Por isso o rendimento é mensal e previsível.

## BDRs

Recibos negociados na B3 que representam ações de empresas estrangeiras. `AAPL34` representa a Apple, `MSFT34` a Microsoft.

- O número final (32, 33, 34, 35) indica o tipo de recibo, não a proporção.
- **Não são a ação em si**: você não tem direito de voto e há um banco depositário no meio.
- O preço embute a variação cambial. Uma BDR pode cair mesmo com a ação subindo lá fora, se o dólar cair mais.

## Criptomoedas

Ativos digitais sem emissor central, negociados 24/7. Bitcoin (`BTC`), Ethereum (`ETH`), Solana (`SOL`), além de stablecoins (`USDT`, `USDC`) atreladas ao dólar.

Características que mudam a análise:
- **Não têm fluxo de caixa.** Não existe P/L, ROE nem DCF. Valuation por múltiplos fundamentalistas simplesmente não se aplica.
- Volatilidade muito maior: quedas de 50%+ em ciclos de baixa são normais historicamente, não excepcionais.
- Mercado 24/7: o gap de abertura não existe, mas você também não tem circuit breaker.

Análise possível: adoção, oferta programada (halving do Bitcoin), fluxo de ETFs, dados on-chain, correlação com ativos de risco.

## Como isso entra na avaliação

Não existe "métrica boa" universal. O que se avalia muda por classe:

| Classe | Métricas centrais |
|---|---|
| Ação | P/L, P/VP, ROE, ROIC, margem, dívida líquida/EBITDA, DY |
| FII | P/VP, DY, vacância, cap rate, duration da carteira |
| ETF | Índice replicado, taxa de administração, tracking error, liquidez |
| BDR | Fundamentos da empresa original + exposição cambial |
| Cripto | Adoção, oferta, liquidez, fluxo institucional |

Aplicar P/L a um FII ou ROE a um Bitcoin é erro de categoria, não análise conservadora.
