# Risco, diversificação e construção de carteira

Retorno é o que se persegue; risco é o que se administra. A maior parte dos erros de investidor pessoa física não está na escolha do ativo, e sim no **tamanho da posição** e na **falta de correlação entre elas**.

## Volatilidade (desvio padrão)

Mede a dispersão dos retornos em torno da média. É a definição operacional mais usada de risco.

```
σ = √[ Σ(retorno_i − retorno_médio)² / (n − 1) ]

Anualização: σ_anual = σ_diário × √252     (252 = pregões no ano)
```

**Referências aproximadas de volatilidade anualizada**:

| Ativo | Faixa típica |
|---|---|
| Tesouro Selic | ~0% |
| Tesouro IPCA+ longo | 8% a 15% |
| Ibovespa | 20% a 30% |
| Ação individual de large cap | 25% a 40% |
| Small cap | 35% a 60% |
| Bitcoin | 50% a 90% |

**A crítica válida à volatilidade como medida de risco**: ela trata alta e queda como igualmente "arriscadas". Ninguém reclama de volatilidade para cima. Por isso existem medidas assimétricas, como o downside deviation (usada no índice de Sortino).

**O que a volatilidade não mede**: risco de perda permanente. Uma ação pode ter volatilidade baixa e ir a zero por fraude ou recuperação judicial. Volatilidade é oscilação; risco de verdade é não recuperar.

## Beta (β)

Sensibilidade do ativo aos movimentos do mercado (no Brasil, o Ibovespa).

```
β = Covariância(ativo, mercado) / Variância(mercado)
```

| β | Leitura |
|---|---|
| 1,0 | Acompanha o mercado |
| > 1,0 | Amplifica: β 1,5 sobe ~15% quando o índice sobe 10% (e cai ~15% quando cai 10%) |
| < 1,0 | Amortece: β 0,6 oscila menos que o índice |
| ≈ 0 | Sem relação com o mercado |
| < 0 | Move na direção oposta (raro; ouro em algumas janelas) |

Setores defensivos (energia elétrica, saneamento, alimentos básicos) tendem a beta baixo. Setores cíclicos (construção, varejo discricionário, commodities) tendem a beta alto.

**Limitação**: beta é calculado sobre o passado e muda com o tempo e com a janela escolhida. Um beta de 3 anos e um de 1 ano podem ser bem diferentes para o mesmo ativo.

## Índice de Sharpe

Retorno por unidade de risco assumido.

```
Sharpe = (Retorno da carteira − Taxa livre de risco) / Volatilidade da carteira
```

| Sharpe | Leitura |
|---|---|
| < 0 | Rendeu menos que a taxa livre de risco — assumiu risco de graça |
| 0 a 0,5 | Fraco |
| 0,5 a 1,0 | Razoável |
| 1,0 a 2,0 | Bom |
| > 2,0 | Excelente (desconfie se for de um período curto) |

**No Brasil o Sharpe é duro**: com a taxa livre de risco em dois dígitos, bater a Selic com sobra é difícil, e muitas carteiras de renda variável apresentam Sharpe baixo ou negativo em janelas de juros altos. Isso não é defeito do cálculo — é a informação relevante.

**Sortino**: variação que usa só a volatilidade das quedas no denominador. Mais adequado para ativos com retorno assimétrico.

## Drawdown

Queda do pico até o fundo, antes de um novo pico.

```
Drawdown = (Valor atual − Valor do pico anterior) / Valor do pico anterior × 100
```

**Máximo drawdown** é a maior dessas quedas no histórico. É a medida de risco mais intuitiva porque corresponde à pergunta real: *"quanto eu teria visto minha carteira cair no pior momento?"*

Duas coisas que o drawdown revela e a volatilidade não:

1. **A assimetria da recuperação.** Uma queda de 50% exige alta de 100% para voltar ao ponto inicial. Queda de 80% exige 400%. Perder muito é matematicamente muito pior que ganhar o mesmo percentual.
2. **O tempo de recuperação.** Um drawdown de 30% que levou 4 anos para ser recuperado é diferente de um de 30% recuperado em 6 meses, ainda que o número seja igual.

**Uso prático**: antes de montar uma posição, olhe o drawdown máximo histórico do ativo e pergunte honestamente se você aguentaria vê-lo acontecer sem vender no fundo. Se não aguentaria, a posição está grande demais.

## Correlação

Mede se dois ativos se movem juntos. Varia de −1 a +1.

| Correlação | Significado |
|---|---|
| +1 | Movem exatamente juntos |
| ~0 | Independentes |
| −1 | Movem em direções opostas |

**Este é o conceito central da diversificação.** Ter 20 ações não diversifica nada se todas forem do mesmo setor e reagirem ao mesmo fator. Cinco bancos brasileiros têm correlação altíssima entre si — na prática é uma posição só, com cinco nomes.

**O que realmente descorrelaciona numa carteira brasileira**:
- Ativos em moeda diferente (BDRs, ETFs internacionais, dólar)
- Renda fixa pós-fixada (que se beneficia justamente quando os juros sobem e a bolsa cai)
- Setores com fatores de risco distintos (exportadora de commodity x varejo doméstico reagem de forma oposta ao câmbio)

**O aviso importante**: as correlações **aumentam em crises**. Justamente no momento em que a diversificação mais importaria, ativos que pareciam independentes caem juntos. Nenhuma carteira de renda variável é imune a isso — por isso liquidez e reserva em renda fixa existem.

## Riscos que os números não capturam

- **Risco de liquidez** — não conseguir vender pelo preço de tela. Sério em small caps, FIIs pequenos e em opções.
- **Risco de crédito** — o emissor não paga.
- **Risco de concentração** — uma posição grande demais domina o resultado.
- **Risco regulatório** — mudança de regra atinge setores regulados (elétricas, bancos, saúde, saneamento).
- **Risco cambial** — receita ou dívida em moeda diferente da sua.
- **Risco de governança** — o pior de todos no Brasil, porque não aparece em nenhum indicador antes de aparecer no preço. Cheque nível de listagem na B3, histórico com minoritários, transações com partes relacionadas.

## Diversificação: o que funciona

**A matemática básica**: o risco específico de uma empresa (o que só afeta ela) cai rápido com a diversificação — a maior parte do benefício já aparece com 15 a 20 ativos **não correlacionados**. O risco de mercado (o que afeta todo mundo) não some com diversificação nenhuma.

**Diversificação de verdade acontece em camadas**:

1. **Classe de ativo** — renda fixa, ações, FIIs, internacional, cripto
2. **Geografia** — Brasil e exterior
3. **Moeda** — real e dólar
4. **Setor** — dentro da parcela de ações
5. **Ativo** — dentro de cada setor

Pular direto para a camada 5 (comprar muitas ações) é o erro mais comum e o menos eficaz.

**Diworsification**: passar de ~30 ativos raramente reduz risco de forma relevante e passa a diluir retorno, além de tornar impossível acompanhar as teses. Mais nomes não é mais diversificação.

## Alocação por perfil de investidor

Os perfis do sistema (CONSERVATIVE, MODERATE, AGGRESSIVE) vêm da suitability — a obrigação regulatória de adequar a recomendação ao investidor. Faixas de referência, não regras:

### CONSERVATIVE (conservador)

Prioridade é preservação de capital. Tolera pouca oscilação; drawdown grande provoca venda no fundo.

- Renda fixa: 70% a 90% (Tesouro Selic, CDBs de banco grande com liquidez, IPCA+ para prazo longo)
- Renda variável: 10% a 25% — preferencialmente ETFs amplos e empresas de setores regulados e pagadoras de dividendos
- FIIs: até 10%
- Cripto: 0% a 2%, se houver

Ênfase da análise: previsibilidade de proventos, dívida baixa, histórico longo, liquidez.

### MODERATE (moderado)

Aceita oscilação em troca de retorno maior no médio e longo prazo.

- Renda fixa: 40% a 60%
- Renda variável: 30% a 45%
- FIIs: 5% a 15%
- Internacional: 5% a 15%
- Cripto: 0% a 5%

Ênfase da análise: equilíbrio entre crescimento e qualidade de balanço; diversificação setorial.

### AGGRESSIVE (arrojado)

Busca retorno alto e aceita drawdowns profundos e prolongados.

- Renda fixa: 10% a 30% (boa parte como reserva de oportunidade)
- Renda variável: 45% a 70%, com espaço para small caps
- Internacional: 10% a 25%
- Cripto: 0% a 10%

Ênfase da análise: teses de crescimento, múltiplos de expansão, catalisadores — sem abandonar a checagem de endividamento, que é o que evita perda permanente.

**Válido para todos os perfis, antes de qualquer alocação**: reserva de emergência de 6 a 12 meses de despesas, em ativo de liquidez diária e risco baixo. Ela não é parte da carteira de investimento — é o que impede a carteira de ser liquidada no pior momento.

## Rebalanceamento

Com o tempo, os pesos saem do alvo: o que subiu ocupa espaço demais, o que caiu encolhe. Rebalancear é voltar aos pesos definidos — o que força vender o que subiu e comprar o que caiu, exatamente o oposto do impulso emocional.

**Frequência**: semestral ou anual costuma bastar. Rebalancear demais gera custo e imposto sem benefício.

**Por banda**: alternativa que só age quando um ativo desvia mais que um limite (por exemplo, 5 pontos percentuais) do peso alvo. Mais eficiente que o calendário fixo.

## O erro que mais custa dinheiro

Não é escolher o ativo errado. É **dimensionar errado** e **vender no fundo**. Uma tese boa em posição grande demais vira insônia, e insônia vira venda na baixa. Position sizing é a parte da gestão de risco que o investidor pessoa física mais ignora e que mais determina o resultado final.
