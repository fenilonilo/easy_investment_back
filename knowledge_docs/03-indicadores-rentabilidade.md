# Indicadores de rentabilidade e margens

Múltiplo diz quanto o ativo custa. Rentabilidade diz **se o negócio presta**. Uma empresa cara com ROIC alto pode ser melhor investimento que uma barata que destrói capital.

## ROI — Retorno sobre Investimento

O mais genérico de todos. Mede o ganho de qualquer investimento em relação ao que foi aplicado.

```
ROI = (Ganho obtido − Custo do investimento) / Custo do investimento × 100
```

**Exemplo**: comprou R$ 10.000 de uma ação, vendeu por R$ 12.500 e recebeu R$ 300 de dividendos no caminho.

```
Ganho total = (12.500 − 10.000) + 300 = 2.800
ROI = 2.800 / 10.000 = 28%
```

**A armadilha central: ROI não tem tempo dentro dele.** 28% em 8 meses e 28% em 6 anos dão o mesmo ROI e são investimentos completamente diferentes. Para comparar, anualize:

```
ROI anualizado = [(1 + ROI)^(1/n) − 1] × 100      (n = número de anos)
```

28% em 6 anos → `(1,28)^(1/6) − 1` = **4,2% a.a.** Abaixo da inflação em boa parte dos anos. O número "28%" sozinho escondia isso.

**Segunda armadilha**: ROI nominal ignora inflação. Com IPCA de 5% a.a., um ROI de 6% a.a. rende 0,95% real. O que importa para o poder de compra é o retorno real:

```
Retorno real = [(1 + retorno nominal) / (1 + inflação)] − 1
```

## ROE — Retorno sobre o Patrimônio Líquido

```
ROE = Lucro líquido / Patrimônio líquido × 100
```

**Leitura**: quanto a empresa gera de lucro para cada R$ 1 que os sócios têm investido nela. É a taxa de retorno do acionista sobre o capital próprio.

**Faixas de referência (Brasil)**:

| ROE | Leitura |
|---|---|
| < 0% | Prejuízo |
| 0% a 10% | Baixo — abaixo da Selic, o capital rende menos que o Tesouro |
| 10% a 15% | Razoável |
| 15% a 20% | Bom |
| > 20% | Excelente, se sustentável e não alavancado |

**Referência obrigatória no Brasil**: compare com a taxa livre de risco. Com a Selic em dois dígitos, um ROE de 12% significa que a empresa remunera o sócio pior que um título público — assumindo todo o risco de renda variável de graça.

**A grande armadilha do ROE: alavancagem.** Pela decomposição DuPont:

```
ROE = Margem líquida × Giro do ativo × Alavancagem
    = (Lucro/Receita) × (Receita/Ativo) × (Ativo/PL)
```

O terceiro fator é dívida. Uma empresa pode dobrar o ROE só se endividando, sem melhorar nada na operação. E patrimônio líquido pequeno (por prejuízos acumulados ou recompras agressivas) infla o ROE artificialmente — no limite, PL negativo produz ROE negativo com lucro positivo, um número sem sentido.

Por isso: **ROE alto só é bom notícia se vier acompanhado de dívida sob controle.** Sempre cheque dívida líquida/EBITDA junto.

## ROIC — Retorno sobre o Capital Investido

```
ROIC = NOPAT / Capital investido × 100

NOPAT = EBIT × (1 − alíquota efetiva de imposto)
Capital investido = Patrimônio líquido + Dívida onerosa − Caixa
```

**Por que é o melhor indicador de qualidade de negócio**: mede o retorno sobre **todo** o capital que financia a operação, próprio e de terceiros. Diferente do ROE, não pode ser inflado por alavancagem — a dívida entra no denominador.

**A comparação que importa: ROIC contra WACC** (custo médio ponderado de capital).

- **ROIC > WACC** → a empresa cria valor. Cada real reinvestido vale mais que um real.
- **ROIC < WACC** → a empresa destrói valor. Crescer piora a situação, porque cresce aplicando capital a um retorno menor que o custo dele.

Esse é o teste que separa negócio bom de negócio grande. Empresa que cresce receita com ROIC abaixo do WACC está queimando dinheiro dos sócios com aparência de expansão.

**Faixas**: acima de 15% costuma indicar vantagem competitiva real (marca, rede, custo de troca, escala). Abaixo de 8% no Brasil, com o custo de capital alto daqui, é preocupante.

## ROA — Retorno sobre o Ativo

```
ROA = Lucro líquido / Ativo total × 100
```

Mede eficiência no uso dos ativos, sem separar o que é capital próprio de terceiros. Útil para bancos e para comparar eficiência operacional dentro de um mesmo setor.

Faixas variam demais entre setores: um banco com ROA de 2% pode ser excelente; um varejista com 2% é fraco. Só compare com pares diretos.

## Margens

Todas partem da DRE e respondem "quanto de cada R$ 100 vendidos vira o quê".

### Margem bruta

```
Margem bruta = (Receita líquida − CPV) / Receita líquida × 100
```

Poder de precificação. Alta indica produto diferenciado, marca ou custo de produção baixo. Software: 70-90%. Varejo alimentar: 20-30%. Distribuição de combustível: 5-8%.

### Margem EBITDA

```
EBITDA = Lucro operacional (EBIT) + Depreciação + Amortização
Margem EBITDA = EBITDA / Receita líquida × 100
```

Geração de caixa operacional antes de juros, impostos e efeitos contábeis não-caixa. É a margem mais usada para comparar operações entre empresas, porque neutraliza estrutura de capital e política de depreciação.

**Cuidado**: EBITDA ignora capex. Em setor intensivo em capital, margem EBITDA de 40% pode conviver com fluxo de caixa livre próximo de zero, porque tudo volta para manutenção de ativo.

### Margem operacional (EBIT)

```
Margem operacional = EBIT / Receita líquida × 100
```

Mais honesta que a EBITDA porque já desconta a depreciação — que é a forma contábil de reconhecer o desgaste dos ativos, um custo real ainda que não seja saída de caixa no período.

### Margem líquida

```
Margem líquida = Lucro líquido / Receita líquida × 100
```

O que sobra no fim de tudo: depois de custos, despesas, juros e impostos. É a margem mais afetada por fatores não operacionais — variação cambial sobre dívida em dólar, resultado financeiro, eventos não recorrentes.

Por isso, margem líquida que oscila muito com EBITDA estável indica que o problema está no financeiro (dívida, câmbio), não na operação.

## Analisando em conjunto

A leitura que responde "esse negócio é bom?":

1. **ROIC vs. WACC** — cria ou destrói valor?
2. **ROE vs. Selic** — remunera melhor que o risco zero?
3. **ROE vs. ROIC** — se o ROE é muito maior que o ROIC, a diferença é alavancagem. Confirme no endividamento.
4. **Margens ao longo de 5 anos** — estáveis, subindo ou comprimindo? Margem que encolhe ano a ano indica perda de poder de precificação ou entrada de concorrência.
5. **Margem EBITDA vs. margem líquida** — a distância entre elas é juros, imposto e depreciação. Distância crescente costuma ser dívida pesando.

Um único ano nunca basta. Rentabilidade se avalia em série histórica, porque o que interessa é **consistência**, não o melhor trimestre.
