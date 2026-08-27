# Métodos de valuation

Valuation não produz "o preço certo". Produz uma **faixa de valor sob premissas explícitas**. O valor de um valuation está menos no número final e mais em obrigar quem analisa a escrever o que está assumindo.

## Fluxo de Caixa Descontado (DCF)

O método mais completo. Parte do princípio de que uma empresa vale a soma de todo o caixa que vai gerar no futuro, trazido a valor presente.

```
Valor da empresa = Σ [ FCFt / (1 + WACC)^t ] + Valor terminal / (1 + WACC)^n
```

### Passo a passo

**1. Projete o fluxo de caixa livre para a firma (FCFF)**, tipicamente 5 a 10 anos:

```
FCFF = EBIT × (1 − alíquota de imposto) + Depreciação − Capex − Δ Capital de giro
```

**2. Calcule o WACC** (custo médio ponderado de capital):

```
WACC = (E/V) × Ke + (D/V) × Kd × (1 − alíquota)

E  = valor de mercado do capital próprio
D  = dívida
V  = E + D
Ke = custo do capital próprio (via CAPM)
Kd = custo da dívida
```

**CAPM** para o custo do capital próprio:

```
Ke = Taxa livre de risco + β × Prêmio de risco de mercado
```

No Brasil a taxa livre de risco costuma ser o Tesouro IPCA+ longo ou a Selic; o prêmio de risco de mercado historicamente é estimado entre 5% e 8%.

**3. Calcule o valor terminal** — o valor de tudo além do horizonte projetado, pelo modelo de perpetuidade de Gordon:

```
Valor terminal = FCF do último ano × (1 + g) / (WACC − g)
```

`g` = crescimento perpétuo. **Regra inegociável: `g` tem que ser menor que o WACC**, e não deve exceder o crescimento de longo prazo da economia (usualmente 2% a 4% nominais em termos reais conservadores). Um `g` acima disso implica que a empresa acabaria maior que o PIB.

**4. Desconte tudo a valor presente e chegue ao Enterprise Value.** Depois:

```
Valor do equity = EV − Dívida líquida
Preço justo por ação = Valor do equity / Número de ações
```

### A fragilidade do DCF

O valor terminal costuma representar **60% a 80% do valor total** num DCF de 5 anos. Ou seja: a maior parte da resposta vem da premissa mais frágil.

E o resultado é extremamente sensível: mudar o WACC de 11% para 12% ou o `g` de 3% para 4% muda o preço justo em dezenas de pontos percentuais. Por isso:

- **Sempre faça análise de sensibilidade**: monte uma matriz de preço justo variando WACC e `g`, e reporte a faixa, não um número.
- Desconfie de qualquer DCF que chegue a um valor com dois decimais. A precisão é falsa.
- Trate-o como ferramenta para entender **quais premissas o preço atual já embute** ("o mercado está assumindo crescimento de 8% a.a. — isso é plausível?"), mais do que para cravar preço-alvo.

### Onde não usar

Empresas sem fluxo de caixa previsível: startups pré-receita, cíclicas no meio do ciclo, empresas em recuperação judicial, criptomoedas (não há fluxo de caixa nenhum).

## Avaliação por múltiplos comparáveis

Muito mais simples e muito usada na prática.

**Método**:
1. Selecione empresas comparáveis — mesmo setor, porte parecido, dinâmica de receita parecida.
2. Calcule a mediana do múltiplo escolhido (P/L, EV/EBITDA, P/VP) no grupo.
3. Aplique essa mediana ao indicador da empresa analisada.

**Exemplo**: EV/EBITDA mediano do setor = 7,0x. A empresa tem EBITDA de R$ 500 milhões e dívida líquida de R$ 1 bilhão.

```
EV justo    = 7,0 × 500 mi          = R$ 3,5 bi
Equity      = 3,5 bi − 1,0 bi       = R$ 2,5 bi
Com 200 mi de ações → preço justo   = R$ 12,50
```

**Vantagem**: rápido, transparente, ancorado no que o mercado paga hoje.

**Limitação central**: assume que o setor está corretamente precificado. Se o setor inteiro está numa bolha, o método diz que tudo está justo. Ele mede **preço relativo**, não valor intrínseco.

**Cuidados**: use mediana e não média (uma empresa com múltiplo distorcido contamina a média); ajuste por diferenças de crescimento e rentabilidade — uma empresa com ROIC muito acima dos pares merece prêmio.

## Fórmula de Graham

Regra prática de Benjamin Graham para triagem rápida de empresas maduras:

```
Valor intrínseco = √(22,5 × LPA × VPA)
```

Onde 22,5 = 15 (P/L máximo aceitável) × 1,5 (P/VP máximo aceitável).

**Exemplo**: LPA = R$ 3,00 e VPA = R$ 20,00.

```
√(22,5 × 3 × 20) = √1.350 ≈ R$ 36,70
```

Ação abaixo desse valor passa no filtro de Graham.

**Limites**: ignora crescimento, dívida, qualidade da gestão e setor. Foi concebida nos anos 1930-1970, num contexto de empresas industriais e ativos tangíveis. Aplicada a empresas de tecnologia, rejeita quase tudo. Use como **filtro de triagem**, jamais como veredito.

Graham também defendia a **margem de segurança**: comprar com desconto relevante (ele falava em 1/3) sobre o valor estimado, justamente porque a estimativa pode estar errada. Esse é o conceito que sobreviveu melhor que a fórmula.

## Método de Bazin

Adaptação brasileira de Décio Bazin, focada em renda por dividendos.

```
Preço teto = Dividendo anual por ação / 0,06
```

A lógica: pagar no máximo um preço que garanta DY de 6% ao ano.

**Exemplo**: ação que paga R$ 2,40 por ano → preço teto = R$ 40,00.

**Regras complementares de Bazin**: só empresas que pagaram dividendos consistentemente nos últimos 5 anos, sem histórico de prejuízo, com endividamento controlado.

**Crítica válida no contexto brasileiro**: o 6% é um número fixo que ignora a taxa de juros vigente. Com a Selic em 14%, exigir apenas 6% de DY é aceitar um prêmio negativo em relação à renda fixa. Uma adaptação sensata é ajustar o divisor ao patamar de juros do momento.

## Modelo de Gordon (crescimento de dividendos)

```
Preço justo = D1 / (Ke − g)

D1 = dividendo esperado no próximo ano
Ke = retorno exigido pelo acionista
g  = taxa de crescimento perpétuo do dividendo
```

**Exemplo**: D1 = R$ 2,00, Ke = 13%, g = 4%.

```
Preço = 2,00 / (0,13 − 0,04) = R$ 22,22
```

**Onde funciona**: empresas maduras, com dividendo estável e crescente — elétricas, saneamento, bancos grandes.

**Onde quebra**: quando `g` se aproxima de `Ke`, o denominador tende a zero e o preço explode ao infinito. Isso não é um resultado, é o modelo saindo do domínio de validade.

## Escolhendo o método

| Situação | Método mais adequado |
|---|---|
| Empresa madura, fluxo previsível | DCF + múltiplos |
| Empresa pagadora de dividendos | Gordon + Bazin ajustado |
| Comparação rápida dentro de um setor | Múltiplos comparáveis |
| Empresa em prejuízo ou pré-lucro | PSR, EV/Receita, múltiplos de usuário/GMV |
| Banco ou seguradora | P/VP com ROE, modelo de dividendos |
| FII | P/VP, cap rate, DY |
| Holding | Soma das partes com desconto de holding |
| Criptomoeda | Nenhum destes — não há fluxo de caixa |

## O que fazer com o resultado

**Nunca use um método só.** Rode dois ou três e veja se convergem. Convergência aumenta confiança; divergência grande indica que uma premissa está fora do lugar — e descobrir qual é mais útil que o número.

**Expresse em faixa**: "entre R$ 28 e R$ 35 sob as premissas X e Y" é honesto. "R$ 31,47" é falsa precisão.

**Explicite as premissas.** Um valuation sem premissas escritas não é analisável nem por quem o fez três meses depois.

**Lembre-se do que o valuation não captura**: qualidade e alinhamento da gestão, governança, risco regulatório, mudança tecnológica, concorrência entrando no setor. Esses fatores frequentemente importam mais que a terceira casa decimal do WACC.
