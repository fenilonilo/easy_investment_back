# Análise técnica

A análise técnica estuda preço e volume para estimar probabilidades de movimento. Não substitui a análise fundamentalista — responde a outra pergunta. Fundamentalista responde *"o que comprar"*; técnica responde *"quando"* e, principalmente, *"onde eu estou errado"*.

**Sobre a validade**: os indicadores abaixo são descritivos, não preditivos. Nenhum deles tem poder de previsão comprovado de forma robusta. O uso defensável é como **disciplina de execução** (definir stop, dimensionar posição, evitar comprar em euforia) e não como oráculo.

## Médias móveis

Preço médio de fechamento dos últimos N períodos, atualizado a cada barra.

- **MMS (simples)** — média aritmética. Mais suave, reage mais devagar.
- **MME (exponencial)** — dá mais peso aos dados recentes. Reage mais rápido, gera mais sinal falso.

**Períodos usuais**: 9 e 21 (curto prazo), 50 (médio), 200 (longo). A de 200 dias é a referência mais acompanhada globalmente para definir tendência primária.

**Leituras**:
- Preço acima da média de 200 → tendência de alta de longo prazo.
- **Golden cross** — média de 50 cruza a de 200 para cima. Lido como sinal de alta.
- **Death cross** — média de 50 cruza a de 200 para baixo. Lido como sinal de baixa.

**A limitação estrutural**: médias móveis são indicadores **atrasados** por construção. O cruzamento acontece depois que boa parte do movimento já ocorreu. Em mercado lateral, geram sinais falsos em série — o padrão conhecido como "serrote".

## RSI — Índice de Força Relativa

Oscilador de 0 a 100 que compara a magnitude dos ganhos recentes com a das perdas. Período padrão: 14.

```
RSI = 100 − [100 / (1 + FR)]
FR  = média dos ganhos / média das perdas nos últimos 14 períodos
```

| RSI | Leitura convencional |
|---|---|
| > 70 | Sobrecomprado |
| 30 a 70 | Neutro |
| < 30 | Sobrevendido |

**O erro mais comum com RSI**: tratar "sobrecomprado" como sinal de venda. Em tendência de alta forte, o RSI **fica** acima de 70 por semanas seguidas, e vender no primeiro toque significa sair no início do movimento. O mesmo vale para 30 em quedas.

**Uso mais defensável — divergência**: o preço faz nova máxima mas o RSI não acompanha (divergência baixista), ou o preço faz nova mínima e o RSI não (divergência altista). Sinaliza perda de força do movimento, o que é mais informativo que o nível absoluto.

## MACD

Diferença entre duas médias exponenciais, com uma linha de sinal por cima.

```
Linha MACD = MME(12) − MME(26)
Linha de sinal = MME(9) da linha MACD
Histograma = Linha MACD − Linha de sinal
```

**Leituras**: MACD cruzando a linha de sinal para cima é lido como altista; para baixo, baixista. O histograma mostra a aceleração — barras encolhendo indicam perda de força mesmo antes do cruzamento.

Mesma limitação das médias: atrasado, e ruim em mercado lateral.

## Bandas de Bollinger

Média móvel de 20 períodos com duas bandas a 2 desvios padrão de distância.

```
Banda superior = MMS(20) + 2σ
Banda central  = MMS(20)
Banda inferior = MMS(20) − 2σ
```

Estatisticamente, ~95% dos preços ficam dentro das bandas quando os retornos são normais — o que na prática não são, especialmente nas caudas.

**Leituras úteis**:
- **Squeeze** (bandas se estreitando) → volatilidade comprimida, frequentemente antecede movimento forte. Não indica a direção.
- Preço tocando a banda superior não é sinal de venda: em tendência forte o preço "anda pela banda".

## Suporte e resistência

- **Suporte** — região de preço onde historicamente aparece compra suficiente para segurar a queda.
- **Resistência** — região onde aparece venda suficiente para segurar a alta.

**Inversão de papel**: resistência rompida com convicção tende a virar suporte, e vice-versa. É o conceito mais robusto da análise técnica, porque tem uma explicação de comportamento plausível — quem vendeu naquele nível e viu o preço subir tende a recomprar quando ele volta.

**Como identificar**: números redondos, máximas e mínimas anteriores relevantes, regiões com muitos toques históricos. Quanto mais toques e mais volume, mais relevante o nível.

## Volume

O único dado da análise técnica que não é derivado do preço, e por isso o mais informativo.

**Regras de leitura**:
- Movimento de preço **com** volume acima da média tem mais convicção.
- Rompimento de resistência **sem** volume costuma falhar.
- Volume secando numa tendência indica esgotamento.
- Pico de volume em queda longa às vezes marca capitulação — os últimos vendedores saindo.

**Detalhe brasileiro**: o volume no vencimento de opções (terceira sexta-feira do mês) e no rebalanceamento do Ibovespa (a cada quadrimestre) é distorcido por fluxo técnico e não deve ser lido como convicção direcional.

## Como integrar com a análise fundamentalista

A combinação que faz sentido:

1. **Fundamento define o "o quê"** — a empresa é boa, o balanço aguenta, o preço faz sentido pelos múltiplos.
2. **Técnica define o "quando" e o "quanto"** — evitar comprar em euforia esticada, escalonar a entrada, definir onde a tese está invalidada.
3. **O stop protege do erro de análise**, não do movimento normal. Um stop apertado demais em ativo volátil é acionado por ruído.

**O que não fazer**: usar análise técnica para justificar segurar um ativo cujo fundamento se deteriorou ("está no suporte"), ou para comprar uma empresa ruim porque "o gráfico está bonito". A técnica não conserta uma tese quebrada.

## Ceticismo saudável

- Indicadores técnicos são funções do preço passado. Nenhum contém informação que o preço já não tenha.
- Backtests de estratégias técnicas sofrem de overfitting com facilidade: com parâmetros suficientes, qualquer regra parece funcionar no histórico.
- Custos de corretagem, spread e imposto (day trade é tributado em 20%, sem isenção) corroem estratégias de giro alto — muitas que parecem lucrativas no papel são negativas líquidas.
- A maior parte dos investidores pessoa física que opera com giro alto perde dinheiro. Isso está documentado em estudos de várias jurisdições, incluindo o Brasil.

O uso mais valioso da análise técnica para o investidor de longo prazo é modesto e defensável: **não comprar tudo de uma vez em um topo eufórico, e ter um plano escrito de onde a tese está errada.**
