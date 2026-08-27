# Lendo as demonstrações financeiras

Todo indicador sai daqui. Quem entende as três demonstrações consegue verificar qualquer múltiplo em vez de aceitá-lo pronto.

## DRE — Demonstração do Resultado do Exercício

Mostra o desempenho de um **período** (trimestre ou ano). Estrutura de cima para baixo:

```
  Receita bruta
− Deduções (impostos sobre vendas, devoluções, descontos)
= RECEITA LÍQUIDA
− CPV / CMV (custo dos produtos ou mercadorias vendidos)
= LUCRO BRUTO
− Despesas com vendas
− Despesas administrativas
± Outras receitas/despesas operacionais
= EBIT (lucro operacional)
± Resultado financeiro (juros pagos, juros recebidos, variação cambial)
= LAIR (lucro antes do IR)
− IR e CSLL
= LUCRO LÍQUIDO
```

**Cada linha responde a uma pergunta**:

- **Receita líquida** — a empresa está vendendo mais? Cresce acima da inflação?
- **Lucro bruto** — sobra margem depois do custo direto? Poder de precificação.
- **EBIT** — a operação em si dá lucro, antes de qualquer efeito de dívida?
- **Resultado financeiro** — quanto a dívida está custando? Linha muito negativa com EBIT saudável significa que a operação é boa mas o balanço está pesado.
- **Lucro líquido** — o que sobra para o acionista.

**EBITDA não está na DRE**. É calculado: `EBITDA = EBIT + Depreciação + Amortização`. Os valores de depreciação estão nas notas explicativas ou na DFC.

**O que procurar**: compare os mesmos períodos de anos diferentes (1T26 com 1T25, não com 4T25) para eliminar sazonalidade. Uma empresa de varejo sempre tem 4º trimestre melhor.

## Balanço Patrimonial

Foto da situação em uma **data**. Sempre equilibrado:

```
ATIVO = PASSIVO + PATRIMÔNIO LÍQUIDO
```

```
ATIVO                              PASSIVO
├─ Circulante                      ├─ Circulante
│  ├─ Caixa e equivalentes         │  ├─ Fornecedores
│  ├─ Contas a receber             │  ├─ Empréstimos de curto prazo
│  ├─ Estoques                     │  └─ Obrigações fiscais/trabalhistas
│  └─ Aplicações financeiras       ├─ Não circulante
└─ Não circulante                  │  ├─ Empréstimos de longo prazo
   ├─ Realizável a longo prazo     │  └─ Provisões
   ├─ Investimentos                └─ PATRIMÔNIO LÍQUIDO
   ├─ Imobilizado                     ├─ Capital social
   └─ Intangível (marcas, ágio)       ├─ Reservas de lucros
                                      └─ Lucros/prejuízos acumulados
```

**Circulante** = realiza ou vence em até 12 meses. **Não circulante** = prazo maior.

**O que procurar**:

- **Caixa vs. dívida de curto prazo** — se o que vence em 12 meses é maior que o caixa, a empresa depende de rolar dívida. Com juros altos, isso encarece o resultado do ano seguinte.
- **Contas a receber crescendo mais rápido que a receita** — sinal clássico de que a empresa está vendendo mais a prazo para segurar o faturamento, ou de inadimplência crescente.
- **Estoque crescendo mais rápido que a receita** — produto encalhando. Em moda e eletrônicos, encalhe vira baixa contábil alguns trimestres depois.
- **Intangível e ágio muito altos** — ágio vem de aquisições. Se as aquisições não entregarem o resultado projetado, vem *impairment*: uma baixa contábil que destrói lucro e patrimônio de uma vez.
- **PL negativo** — passivo maior que ativo. Situação grave; a maior parte dos indicadores baseados em PL (ROE, P/VP) para de fazer sentido.

## DFC — Demonstração dos Fluxos de Caixa

A mais difícil de manipular e por isso a mais reveladora. Divide o caixa em três origens:

### Fluxo de caixa operacional (FCO)

Dinheiro gerado pela operação. Parte do lucro líquido e ajusta o que não é caixa (depreciação, provisões) e as variações de capital de giro.

**É a linha mais importante da demonstração inteira.** Lucro é opinião contábil; caixa operacional é fato.

**Sinal de alerta forte**: lucro líquido crescendo com FCO estagnado ou negativo. Significa que o lucro está virando contas a receber ou estoque, não dinheiro. Empresas em fraude ou em deterioração costumam mostrar esse padrão antes de qualquer outro indicador piorar.

### Fluxo de caixa de investimento (FCI)

Compra e venda de ativos de longo prazo. A linha principal é o **capex** (investimento em imobilizado).

- **Capex de manutenção** — o necessário para manter a capacidade atual.
- **Capex de expansão** — para crescer.

A empresa raramente separa os dois; uma aproximação usa a depreciação como proxy do capex de manutenção.

### Fluxo de caixa de financiamento (FCF)

Captação e pagamento de dívida, emissão e recompra de ações, dividendos pagos.

**A leitura mais útil da DFC** é a combinação dos sinais:

| FCO | FCI | FCFin | Perfil |
|---|---|---|---|
| + | − | − | Empresa madura saudável: gera caixa, investe e devolve ao acionista |
| + | − | + | Crescimento: gera caixa, investe pesado e ainda capta |
| − | − | + | Queima caixa financiada por dívida — insustentável |
| + | + | − | Vendendo ativos para pagar dívida — reestruturação |

## Fluxo de Caixa Livre (FCL)

```
FCL = Fluxo de caixa operacional − Capex
```

O dinheiro que sobra depois de manter e expandir o negócio. É o que pode virar dividendo, recompra ou amortização de dívida sem prejudicar a operação.

**Por que é a métrica mais honesta**: não depende de julgamento contábil sobre depreciação, provisão ou reconhecimento de receita. É dinheiro que entrou menos dinheiro que saiu.

**Yield de FCL**:

```
FCF Yield = FCL / Valor de mercado × 100
```

Um FCF yield de 12% significa que a empresa gera, por ano, 12% do próprio valor de mercado em caixa livre. É a métrica que mais se aproxima do "retorno econômico real" da ação.

**Volatilidade**: o FCL oscila muito entre anos por causa do capex. Um ano de investimento pesado derruba o FCL sem que o negócio tenha piorado. Use média de 3 a 5 anos.

## Sinais de alerta na leitura conjunta

1. **Lucro sobe, FCO não acompanha** — o lucro não está virando dinheiro.
2. **Receita cresce, margem bruta cai** — está comprando faturamento com desconto.
3. **Contas a receber e estoque crescem mais que a receita** — capital de giro consumindo caixa.
4. **Resultado financeiro cada vez mais negativo** — dívida corroendo o resultado.
5. **Muitos "eventos não recorrentes" recorrentes** — quando todo trimestre tem um ajuste extraordinário, ele não é extraordinário.
6. **Ágio alto sem geração de caixa correspondente** — risco de impairment.
7. **Mudança de política contábil ou troca de auditor** sem explicação clara.

## Ordem prática de leitura

Para avaliar um ativo a partir dos demonstrativos, na prática:

1. **DFC primeiro** — a empresa gera caixa? (FCO positivo e crescente)
2. **DRE em série de 5 anos** — receita e margens, tendência e não nível.
3. **Balanço** — dívida, caixa, capital de giro.
4. **Notas explicativas** — onde ficam as coisas desconfortáveis: cronograma da dívida, contingências judiciais, partes relacionadas, garantias.
5. **Só então** calcule múltiplos e rentabilidade.

Quem começa pelo P/L está aceitando o número que alguém calculou, sem saber de qual lucro ele veio.
