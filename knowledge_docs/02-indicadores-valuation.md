# Múltiplos de valuation

Múltiplo responde a uma pergunta só: **quanto o mercado está pagando por cada unidade de alguma coisa que a empresa produz** (lucro, patrimônio, receita, caixa). Múltiplo isolado não diz se está caro ou barato — só faz sentido comparado com (a) o setor, (b) a própria história do ativo, (c) o crescimento esperado.

## P/L — Preço sobre Lucro

```
P/L = Preço da ação / Lucro por ação (LPA)
    = Valor de mercado / Lucro líquido dos últimos 12 meses
```

**Leitura**: quantos anos de lucro atual seriam necessários para pagar o preço da ação, mantido tudo constante. P/L 8 = 8 anos.

**Faixas de referência (B3)**:

| Faixa | Leitura usual |
|---|---|
| < 6 | Barato ou com problema sério (lucro não recorrente, risco regulatório, setor em declínio) |
| 6 a 12 | Faixa comum de empresas maduras brasileiras |
| 12 a 20 | Prêmio por crescimento ou por previsibilidade |
| > 20 | Expectativa forte de crescimento embutida |
| Negativo | Empresa com prejuízo — o múltiplo perde sentido, não use |

**Armadilhas**:
1. **Lucro não recorrente infla o denominador.** Venda de ativo, reversão de provisão ou crédito tributário derrubam o P/L artificialmente. Sempre olhe o lucro recorrente.
2. **Setores cíclicos invertem o sinal.** Mineradora e siderúrgica ficam com P/L baixíssimo no topo do ciclo (lucro no pico) e altíssimo no fundo. P/L baixo em cíclica costuma ser alerta, não oportunidade.
3. **P/L não vê dívida.** Duas empresas com o mesmo P/L e alavancagens opostas não são comparáveis. Para isso existe o EV/EBITDA.
4. **Bancos e seguradoras** têm dinâmica própria de balanço; compare só com pares do mesmo setor.

## P/VP — Preço sobre Valor Patrimonial

```
P/VP = Preço da ação / Valor patrimonial por ação (VPA)
     = Valor de mercado / Patrimônio líquido
```

**Leitura**: quanto o mercado paga por cada R$ 1 de patrimônio contábil.

- **P/VP < 1**: o mercado precifica a empresa abaixo do valor contábil. Ou está barata, ou o mercado acha que aquele patrimônio vale menos do que diz o balanço (ativos obsoletos, prejuízo à frente).
- **P/VP > 3**: comum em empresas de serviço/tecnologia, onde o valor está em marca, software e pessoas — coisas que quase não aparecem no ativo contábil.

**Onde funciona melhor**: bancos, seguradoras, holdings e FIIs, onde o patrimônio é composto de ativos financeiros marcados de forma próxima ao valor real.

**Onde engana**: empresas de tecnologia e serviços, cujo ativo principal não está no balanço.

Vale a relação: **P/VP ≈ P/L × ROE**. Um P/VP alto só se justifica com ROE alto.

## EV/EBITDA

```
EV (Enterprise Value) = Valor de mercado + Dívida líquida
EV/EBITDA = EV / EBITDA dos últimos 12 meses
```

**Leitura**: quanto custaria comprar a operação inteira, dívida incluída, por unidade de geração de caixa operacional.

**Por que é melhor que P/L para comparar empresas**: neutraliza estrutura de capital (dívida), política de depreciação e regime tributário. Duas empresas iguais na operação e diferentes no endividamento têm P/L diferente e EV/EBITDA parecido.

**Faixas**: abaixo de 5 costuma ser barato; 5 a 9 é a faixa comum; acima de 12 já embute crescimento relevante.

**Armadilhas**:
- EBITDA **não é caixa**. Ignora capex, juros e imposto. Empresa intensiva em capital (telecom, saneamento, mineração) parece muito mais barata pelo EBITDA do que é.
- Não use em banco: o conceito de dívida líquida não se aplica a instituição financeira.

## PSR — Preço sobre Receita (P/S)

```
PSR = Valor de mercado / Receita líquida dos últimos 12 meses
```

Serve quando não há lucro: empresa em prejuízo, em fase de crescimento acelerado, ou em recuperação.

Só compara dentro do mesmo setor: uma varejista com margem de 3% e uma de software com margem de 30% nunca terão PSR comparável.

## PEG — P/L ajustado ao crescimento

```
PEG = P/L / taxa de crescimento anual esperada do lucro (em %)
```

Exemplo: P/L 30 com crescimento esperado de 30% a.a. → PEG = 1,0.

**Regra de bolso (Peter Lynch)**: PEG ≈ 1 é preço justo; abaixo de 1 sugere que o crescimento não está totalmente precificado; acima de 2 exige convicção grande.

**Fragilidade**: depende inteiramente de uma projeção de crescimento. Troque a estimativa e o PEG muda de "barato" para "caro" sem que nada tenha mudado na empresa. Trate como sanity check, não como veredito.

## P/FCF — Preço sobre Fluxo de Caixa Livre

```
FCF (Fluxo de Caixa Livre) = Caixa das operações − Capex
P/FCF = Valor de mercado / FCF dos últimos 12 meses
```

O mais próximo da verdade econômica: caixa que sobra depois de manter o negócio funcionando. É o dinheiro que pode virar dividendo, recompra ou redução de dívida.

Mais difícil de manipular contabilmente que o lucro, e por isso mais confiável. Em compensação, oscila muito de ano para ano (um capex grande derruba o FCF de um período sem significar piora do negócio). Olhe a média de 3 a 5 anos.

## Dividend Yield

Coberto em detalhe no documento de dividendos. Em resumo: `DY = Proventos por ação nos últimos 12 meses / Preço da ação`.

## Como usar em conjunto

Nenhum múltiplo decide sozinho. Uma leitura mínima honesta cruza:

1. **P/L e EV/EBITDA** → o preço em relação ao que a empresa gera.
2. **P/VP com ROE** → o preço em relação ao patrimônio, validado pela rentabilidade.
3. **Dívida líquida/EBITDA** → se o preço "barato" não é reflexo de risco de balanço.
4. **Histórico do próprio ativo** → o múltiplo está acima ou abaixo da própria média de 5 anos?
5. **Pares do setor** → o setor inteiro está barato, ou só esta empresa?

Quando um ativo aparece barato em todos os múltiplos ao mesmo tempo, a pergunta certa não é "por que não comprar" e sim **"o que o mercado está vendo que eu não estou vendo"**. Isso se chama value trap: barato porque o lucro vai encolher.
