# Macroeconomia e o mercado brasileiro

> **Aviso de vigência**: os valores numéricos de indicadores neste documento são de **agosto de 2026**. Indicadores macro mudam constantemente — sempre confirme o valor corrente antes de usar em uma análise. As relações de causa e efeito descritas continuam válidas independentemente do nível.

## Selic

Taxa básica de juros da economia brasileira, definida pelo Copom (Comitê de Política Monetária do Banco Central) em reuniões a cada 45 dias, oito vezes por ano.

**Patamar em agosto de 2026: 14,00% ao ano** (definida na reunião de 05/08/2026).

**Por que é o indicador mais importante para o investidor brasileiro**:

1. **É o custo de oportunidade de tudo.** Qualquer investimento de risco precisa oferecer retorno esperado acima da Selic para fazer sentido. Com Selic a 14%, um DY de 8% ou um ROE de 12% são, em termos relativos, ruins.
2. **Entra no denominador de todo valuation.** Selic alta aumenta a taxa livre de risco, aumenta o WACC, e reduz o valor presente dos fluxos futuros. Empresas de crescimento — cujo valor está concentrado em fluxos distantes — sofrem desproporcionalmente.
3. **Encarece a dívida das empresas.** Boa parte da dívida corporativa brasileira é atrelada ao CDI. Selic subindo transfere resultado do acionista para o credor.
4. **Puxa fluxo para fora da bolsa.** Com renda fixa pagando dois dígitos com risco baixo, o prêmio exigido para ficar em renda variável aumenta.

**Efeito prático nas classes de ativo**:

| Movimento | Beneficia | Prejudica |
|---|---|---|
| Selic subindo | Bancos, seguradoras, pós-fixados, empresas com caixa líquido | Empresas endividadas, growth, construção, varejo, prefixados marcados a mercado |
| Selic caindo | Growth, construção, varejo, small caps, FIIs de tijolo, prefixados | Margem financeira de bancos, retorno do pós-fixado |

## IPCA

Índice de Preços ao Consumidor Amplo, calculado pelo IBGE. É a inflação oficial e a meta perseguida pelo Banco Central.

**Onde importa para o investidor**:

- **Retorno real**. É o que interessa de fato:

```
Retorno real = [(1 + retorno nominal) / (1 + IPCA)] − 1
```

Um CDB rendendo 13% com IPCA de 5% entrega ~7,6% reais, não 8%.

- **Tesouro IPCA+** paga IPCA mais um cupom fixo, protegendo o poder de compra.
- **Repasse de preços**: empresas com poder de precificação (marca forte, concessão com reajuste contratual) repassam inflação e defendem margem. Empresas em setores competitivos absorvem e veem a margem comprimir.
- IPCA alto pressiona o Copom a subir a Selic — a ligação entre os dois é direta.

## Câmbio (dólar/real)

O real é uma moeda de mercado emergente, e o câmbio é volátil por natureza.

**Quem ganha com dólar alto**: exportadoras e empresas com receita dolarizada — mineração (`VALE3`), papel e celulose (`SUZB3`), proteína animal (`JBSS3`), petróleo.

**Quem perde**: empresas com custo ou dívida em dólar e receita em real — aéreas, importadoras, varejo de eletrônicos.

**Efeito de segunda ordem**: dólar alto pressiona inflação de bens comercializáveis, o que pressiona o IPCA, que pressiona a Selic. Os três indicadores estão encadeados.

**Para o investidor**: exposição cambial é uma das poucas formas realmente eficazes de descorrelacionar uma carteira brasileira, porque o dólar tende a subir justamente nos momentos de estresse local.

## CDI

Taxa dos empréstimos interbancários de um dia. Na prática roda muito próxima da Selic (poucos centésimos abaixo).

É o **benchmark da renda fixa brasileira**: CDBs, LCIs, fundos DI e debêntures são cotados como percentual do CDI ("110% do CDI") ou como CDI mais spread ("CDI + 2%").

## B3 e índices

- **Ibovespa (IBOV)** — principal índice, composto pelos ativos mais negociados, ponderado por free float ajustado por liquidez. Rebalanceado a cada quadrimestre.
- **IBrX 100** — 100 ativos mais líquidos, ponderação diferente.
- **SMLL** — small caps.
- **IDIV** — carteira de maiores pagadoras de dividendos.
- **IFIX** — índice de fundos imobiliários.

**Característica estrutural do Ibovespa**: alta concentração em commodities e bancos. Isso significa que o índice é fortemente influenciado por preço de minério, petróleo e pelo ciclo de crédito — e não representa bem a economia doméstica diversificada.

## Formação de tickers na B3

O formatador de tickers desta API segue estas regras:

| Padrão | Regra | Exemplo |
|---|---|---|
| Ação/FII/ETF brasileiro | 5+ caracteres terminando em dígito → sufixo `.SA` | `PETR4` → `PETR4.SA` |
| Criptomoeda | Símbolo conhecido → sufixo `-USD` | `BTC` → `BTC-USD` |
| Ação americana | Passa sem alteração | `AAPL` → `AAPL` |

O sufixo `.SA` (São Paulo) é a convenção do Yahoo Finance para ativos da B3. Sem ele, a consulta a `PETR4` retorna vazio ou um ativo errado de outra bolsa.

## Horários de negociação

| Mercado | Pregão regular (horário de Brasília) |
|---|---|
| B3 | 10h00 às 17h00 (leilão de fechamento até ~17h30); after-market ~17h30 às 18h00 |
| NYSE / Nasdaq | 10h30 às 17h00 (com o horário de verão americano: 11h30 às 18h00) |
| Cripto | 24 horas, 7 dias por semana |

Os horários americanos variam duas vezes por ano por causa do horário de verão nos EUA, que o Brasil não adota mais.

## Tipos de ordem

| Tipo | Comportamento |
|---|---|
| **A mercado** | Executa imediatamente ao melhor preço disponível. Garante execução, não garante preço |
| **Limitada** | Só executa até o preço definido. Garante preço, não garante execução |
| **Stop loss** | Vira ordem de venda quando o preço cai até o gatilho. Serve para limitar perda |
| **Stop gain** | Vira ordem de venda quando o preço sobe até o gatilho. Realiza lucro |
| **Start** | Vira ordem de compra quando o preço sobe até o gatilho. Entrada em rompimento |

**Cuidado com ordem a mercado em ativo ilíquido**: o livro pode estar raso e a execução sair muito distante da última cotação. Em small caps e FIIs pequenos, use sempre ordem limitada.

## Circuit breaker

Mecanismo de interrupção automática do pregão em quedas bruscas do Ibovespa:

- Queda de 10% → pregão interrompido por 30 minutos
- Queda de 15% (após a retomada) → interrompido por 1 hora
- Queda de 20% → a B3 decide sobre a suspensão

Existe para evitar espirais de pânico e dar tempo de precificação. Foi acionado várias vezes em março de 2020.

## Tributação de operações (pessoa física)

| Operação | Alíquota | Isenção |
|---|---|---|
| Ações — swing trade | 15% sobre o ganho | Vendas até R$ 20.000/mês no total: ganho isento |
| Ações — day trade | 20% sobre o ganho | Nenhuma |
| FIIs — ganho na venda | 20% | Nenhuma |
| FIIs — rendimento mensal | Isento (com condições) | Ver documento de dividendos |
| ETFs de ações | 15% (swing) / 20% (day) | Nenhuma — não vale o limite de R$ 20 mil |
| Criptomoedas | 15% a 22,5% (progressivo por faixa de ganho) | Vendas até R$ 35.000/mês: ganho isento |
| BDRs | 15% | Nenhuma |

**Mecânica**: o imposto é apurado e pago pelo próprio investidor via **DARF**, até o último dia útil do mês seguinte ao da venda, código 6015. Há retenção de 0,005% na fonte no swing trade (o "dedo-duro", que informa a Receita) e 1% no day trade.

**Compensação de prejuízos**: prejuízo pode ser compensado com lucro futuro da mesma modalidade, sem prazo de validade. Prejuízo de day trade só compensa lucro de day trade. Manter o controle mensal é obrigação do investidor — a corretora não faz isso.

**Dividendos e JCP** têm regra própria, mudada em 2026. Ver o documento de dividendos.

## Como o cenário macro muda a análise de um ativo

Um mesmo ativo tem leituras diferentes conforme o cenário:

**Juros altos (cenário atual)**:
- Priorize empresas com dívida líquida baixa ou caixa líquido
- Prêmio de risco exigido sobe: um DY de 8% compete com 14% sem risco
- Empresas de crescimento sofrem mais na marcação
- Bancos e seguradoras se beneficiam do spread

**Juros em queda**:
- Empresas alavancadas ganham fôlego, o resultado financeiro melhora
- Setores sensíveis a crédito reagem primeiro (construção, varejo, small caps)
- FIIs de tijolo se valorizam (o custo de oportunidade cai)

**Dólar alto**: exportadoras ganham, importadoras perdem, inflação pressiona.

Analisar um ativo sem olhar o cenário de juros no Brasil é ignorar a variável que mais mexe no preço.
