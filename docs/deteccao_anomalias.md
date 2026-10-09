# Detecção de anomalias: como funciona e por quê

Este documento explica o módulo [`streamlit/app/utils/anomalias.py`](../streamlit/app/utils/anomalias.py)
e as funções de SHAP de [`pipeline.py`](../streamlit/app/utils/pipeline.py): o algoritmo, cada
decisão de modelagem e os números das bases que sustentam essas decisões.

Salvo indicação, os números são da base `contratos_ceara.csv` (22.631 linhas brutas,
22.324 após o tratamento) e foram obtidos rodando o próprio pipeline do projeto.

---

## 1. Onde a detecção entra

```
CSV do PNCP -> tratamento -> classificação -> população -> detecção de anomalias -> painel
               tratamento.py  classificador.py  ibge.py     anomalias.py             app.py
                              (22 categorias)   (Censo 2022)
```

A detecção recebe os contratos já limpos, com categoria e população do município, e
devolve para cada contrato: nível de risco (Alto, Médio, Baixo ou Não avaliado), um
índice de 0 a 100, o texto com os principais fatores (vindo do SHAP) e os alertas de
cadastro.

---

## 2. O Isolation Forest em uma página

**Por que um método não supervisionado.** Os dados do PNCP não dizem quais contratos
são irregulares. Sem esse rótulo não dá para treinar um classificador. O que dá para
fazer é procurar os contratos que fogem do padrão dos demais, e é isso que o Isolation
Forest (Liu, Ting e Zhou, 2008) faz.

**A ideia.** Em vez de descrever o que é normal, o algoritmo mede o quão fácil é isolar
cada contrato:

1. sorteia 256 contratos do grupo;
2. escolhe um atributo ao acaso e um ponto de corte ao acaso entre o mínimo e o máximo
   desse atributo, e divide os contratos em dois lados;
3. repete em cada lado até cada contrato ficar sozinho ou a árvore chegar à
   profundidade 8 (= log2 256);
4. constrói 300 árvores assim.

Um contrato muito diferente dos outros fica sozinho depois de poucos cortes. Um contrato
comum, cercado de contratos parecidos, precisa de muitos. O número de cortes até isolar é
o **tamanho do caminho** h(x).

**O score.**

```
s(x) = 2 ^ ( -E[h(x)] / c(256) )
```

- `E[h(x)]`: tamanho médio do caminho nas 300 árvores.
- `c(n) = 2(ln(n-1) + 0,5772) - 2(n-1)/n`: tamanho médio do caminho numa árvore binária
  com n pontos. Com n = 256, c = 10,245. Serve só para normalizar. Também estima quantos
  cortes ainda faltariam quando uma folha para com vários contratos juntos.
- s perto de 1 = atípico; s bem abaixo de 0,5 = normal. O sklearn devolve `-s(x)` em
  `score_samples`.

No grupo Municipal · Contrato, s vai de 0,335 a 0,796, com mediana de 0,385. O corte do
risco Alto (percentil 95) fica em 0,597. Em cortes: o contrato mediano precisa de 14,1
cortes para ser isolado, e os 5% mais atípicos precisam de 7,6 ou menos.

**Duas propriedades do algoritmo que guiaram a escolha dos atributos:**

1. **Escala não importa, forma importa.** Como o corte é sorteado entre o mínimo e o
   máximo, multiplicar um atributo por uma constante não muda nada. O que muda o
   resultado é: transformação não linear (log), normalização por categoria (cada
   categoria com seu próprio centro e escala) e o ponto em que o atributo é "cortado" em
   zero (seção 4.7).
2. **Nos nós profundos, qualquer diferença conta.** O corte é sorteado entre o mínimo e o
   máximo *daquele nó*. Num nó em que só sobraram contratos com valores pequenos, o
   algoritmo separa 0 de 0,003 tão bem quanto separaria 0 de 2. Um atributo com muitos
   valores "um pouquinho acima de zero" ganha poder de isolamento sem que isso signifique
   risco. Foi isso que gerou o problema da vigência (seção 6).

---

## 3. O que foi feito, passo a passo (`detectar_anomalias`)

1. **Alertas de cadastro, fora do risco.** Valor até R$ 100, vigência que termina antes de
   começar, contrato de até 1 dia e assinatura depois da publicação no PNCP: 298 contratos.
   São erros de preenchimento e seriam os pontos mais fáceis de isolar. Se entrassem no
   modelo, dominariam o topo do ranking.
2. **Exclusões ("Não avaliado").** Alienações (venda de bens pelo governo, que é receita e
   não despesa): 414 contratos. Grupos com menos de 50 contratos: 11 contratos.
3. **Grupos de comparação.** Esfera do órgão x tipo de documento (contrato ou empenho).
   Cada grupo tem o seu próprio modelo:

   | Grupo                    | Contratos | Atributos                                            |
   |--------------------------|----------:|------------------------------------------------------|
   | Municipal · Contrato     |    11.429 | valor por habitante, vigência, concentração, recorrência |
   | Estadual · Empenho       |     5.277 | valor, concentração, recorrência                     |
   | Estadual · Contrato      |     3.502 | valor, vigência, concentração, recorrência           |
   | Federal · Empenho        |       983 | valor, concentração, recorrência                     |
   | Federal · Contrato       |       501 | valor, vigência, concentração, recorrência           |
   | Não se aplica · Contrato |       207 | valor, vigência, concentração, recorrência           |
   | Municipal · Empenho      |         7 | não avaliado (menos de 50)                           |
   | Não se aplica · Empenho  |         4 | não avaliado (menos de 50)                           |

4. **Atributos** calculados por grupo (seção 4).
5. **Um Isolation Forest por grupo**: 300 árvores, 256 contratos por árvore, semente 42
   (a mesma base dá sempre o mesmo resultado).
6. **Score -> percentil -> nível.** Alto = 5% mais atípicos do grupo; Médio = os 10%
   seguintes; Baixo = o resto. O score bruto de modelos diferentes não é comparável entre
   si, o percentil dentro do grupo é. Por isso não se usa o parâmetro `contamination` do
   sklearn, que só fixaria um limiar sobre o score.
7. **SHAP** para os contratos Alto e Médio, que vira o texto "Principais fatores" (seção 5).

Resultado: 21.899 contratos avaliados, 1.099 Alto e 2.186 Médio.

> O nível de risco é uma **fila de prioridade para auditoria**, não uma estimativa de
> quantos contratos são irregulares. Por construção, 5% de cada grupo serão sempre
> "Alto", mesmo numa base sem nenhuma irregularidade.

---

## 4. Por que esses atributos

Cada atributo precisava cumprir quatro critérios:

- **ter sentido de risco** (sobrepreço, direcionamento a um fornecedor);
- **ser comparável** entre os contratos do mesmo grupo;
- ter uma distribuição em que **"longe do típico" signifique "fácil de isolar"**;
- **não repetir** a informação de outro atributo.

### 4.1 Valor (em log, comparado com a categoria)

| Estatística (contratos avaliados) | Valor              |
|-----------------------------------|--------------------|
| Mediana                           | R$ 20.199          |
| Percentil 99                      | R$ 7,08 milhões    |
| Máximo                            | R$ 2,19 bilhões    |
| Assimetria (bruto / log)          | 84,4 / 0,08        |
| Valor nos 1% maiores contratos    | 74% do total       |

- **Por que log.** Na escala original, o contrato de R$ 2,19 bilhões sozinho ocupa quase
  todo o intervalo [mínimo, máximo]. Os cortes aleatórios caem quase sempre no vazio entre
  a massa de contratos e os gigantes. Os gigantes são isolados, mas um contrato 10x acima
  do típico fica misturado aos normais. No log, "10x acima" é a mesma distância em
  qualquer faixa de valor, e a distribuição fica simétrica (assimetria 0,08).
- **Por que comparar com a categoria.** A mediana muda até 20x entre categorias no grupo
  Municipal · Contrato: Material de limpeza R$ 17,9 mil, Obras e engenharia R$ 251 mil,
  Transporte escolar R$ 364 mil. Sem essa comparação, uma obra é "cara" só por ser obra.
  No experimento sem a categoria, Obras sobe de 13,8% para 22,7% dos contratos Alto (é 9%
  do grupo), e Combustíveis de 9,4% para 12,9%.
- **Por que mediana e MAD, e não média e desvio-padrão.**
  `z = (x - mediana) / (1,4826 x MAD)`, com MAD = mediana de |x - mediana|. A média e o
  desvio-padrão são puxados justamente pelos contratos extremos que queremos achar: um
  contrato de R$ 2 bilhões infla o desvio-padrão e "esconde" os demais. A mediana e a MAD
  só se movem se mais da metade dos dados mudar. O 1,4826 põe a MAD na escala do
  desvio-padrão (para dados normais).
- Categorias com menos de 5 contratos no grupo usam a mediana e a escala do grupo inteiro.

### 4.2 Valor por habitante, nos municipais: ponto de atenção

A ideia era comparar municípios de tamanhos diferentes: R$ 1 milhão em Fortaleza
(2,4 milhões de habitantes) não é o mesmo que R$ 1 milhão num município de 5 mil. **Os
dados não confirmam essa premissa para contratos individuais:**

| Medida (Municipal · Contrato)                         | Correlação de Spearman com a população |
|-------------------------------------------------------|------:|
| Valor de cada contrato                                | 0,06  |
| Número de contratos por município                     | 0,41  |
| Valor total por município                             | 0,56  |

A mediana do valor por contrato é R$ 46,6 mil nos municípios com mais de 500 mil
habitantes e R$ 40,0 mil nos com menos de 20 mil. Municípios maiores fazem **mais**
contratos, não contratos **maiores**. Dividir o valor de um contrato pela população cria
um viés de porte:

| Faixa de população | % do grupo | % do Alto, por habitante (atual) | % do Alto, valor sem dividir |
|--------------------|-----------:|---------------------------------:|-----------------------------:|
| até 20 mil         | 25,4       | 29,9                             | 24,3                         |
| 20 a 50 mil        | 34,0       | 47,6                             | 42,5                         |
| 50 a 100 mil       | 28,1       | 17,1                             | 21,7                         |
| 100 a 500 mil      | 9,0        | 3,1                              | 7,7                          |
| mais de 500 mil    | 3,4        | 2,3                              | 3,8                          |

Com o valor por habitante, municípios de 100 a 500 mil habitantes têm um terço da
presença esperada no Alto. Sem a divisão, as proporções ficam próximas das da base.

**Recomendação:** usar o valor sem dividir pela população também nos municipais (a
comparação com a categoria continua valendo). O valor por habitante faz sentido para
agregados, como o total por município no mapa, e não para cada contrato. **Isso não foi
alterado no código**, porque é uma decisão de metodologia. Para mudar, basta fazer
`usa_habitante = False` em `detectar_anomalias`. Com a mudança, 457 dos 572 contratos Alto
do grupo continuam Alto.

### 4.3 Vigência (só contratos)

- **Empenhos ficam de fora:** 98% deles terminam em 31/12. Valem até o fim do exercício
  financeiro, então a "vigência" de um empenho mede só a data em que ele foi emitido.
- **Muito concentrada em 12 meses:** 62% dos contratos têm entre 360 e 366 dias, e as
  medianas por categoria vão de 334 a 365 dias.
- **Como é medida:** log da razão entre a duração e a mediana da categoria, contando só o
  que passar de 10% acima da mediana. Não divide pela MAD, porque com tantos contratos de
  12 meses a MAD fica perto de zero (seção 6). O dobro da mediana dá log 2 - log 1,1 = 0,6.
- Com isso, 99% dos contratos municipais ficam em 0 (no padrão), e o atributo só pesa
  para contratos realmente longos. Exemplo: 1.826 dias numa categoria com mediana de um
  ano ("Vigência de 1.826 dias, 5,0x a mediana da categoria").

### 4.4 Concentração no mesmo fornecedor

```
fatia       = valor do órgão que foi para o fornecedor / valor total do órgão
vezes_media = fatia / (1 / nº de fornecedores do órgão) = fatia x nº de fornecedores
```

- **Por que relativo ao número de fornecedores:** 7% num órgão com 300 fornecedores é 21x
  a fatia média, enquanto 30% num órgão com 3 fornecedores é 0,9x. O primeiro é bem mais
  concentrado.
- **Referência = 1x (a fatia média):** só conta como risco o fornecedor que recebe mais
  que a média do órgão. No grupo Municipal · Contrato, a mediana de `vezes_media` é 0,39x,
  o percentil 90 é 3,8x e 30% dos contratos estão acima de 1x. A mediana fica abaixo de 1x
  porque, em cada órgão, poucos fornecedores ficam com quase todo o valor e a maioria
  recebe pouco.
- Calculada sobre a base inteira carregada, por órgão comprador (CNPJ), sem as
  alienações. Só para órgãos com pelo menos 5 contratos e fornecedor identificado. Nos
  demais casos o valor é neutro (1x).
- **Limitação:** um órgão que comprou tudo de um único fornecedor tem `vezes_media` = 1
  (ele *é* a média). Esse caso aparece pela recorrência.

### 4.5 Recorrência

- Quantos contratos o mesmo fornecedor tem com o mesmo órgão. No grupo Municipal ·
  Contrato: mediana de 2, percentil 95 de 18, máximo de 56.
- Em log1p (1 -> 2 contratos importa mais que 40 -> 41), comparado com a mediana do grupo
  (não há uma referência natural como o 1x da concentração).
- **Efeito do registro de preços:** uma ata de registro de preços gera vários contratos
  com o mesmo fornecedor. Esses contratos são 16% do grupo e 21% do Alto, e a recorrência
  explica 44% do peso deles. Em Material de expediente, a recorrência chega a 64% do peso
  dos contratos Alto. É um padrão real de concentração de compras, mas vale lembrar dele ao
  interpretar.

### 4.6 Os atributos se complementam

Correlação de Spearman entre os atributos que entram no modelo (Municipal · Contrato):

|              | valor/hab | vigência | concentração | recorrência |
|--------------|------:|------:|------:|------:|
| valor/hab    | 1,00  | 0,04  | 0,38  | -0,13 |
| vigência     | 0,04  | 1,00  | 0,03  | -0,06 |
| concentração | 0,38  | 0,03  | 1,00  | 0,29  |
| recorrência  | -0,13 | -0,06 | 0,29  | 1,00  |

A maior correlação é 0,38 (contratos caros tendem a aumentar a fatia do fornecedor, o que
é esperado). Nenhum atributo repete o outro.

### 4.7 Só o lado de cima conta (corte em zero)

O Isolation Forest é simétrico: um contrato muito *barato* é tão fácil de isolar quanto um
muito caro. Mas valor baixo, vigência curta ou pouca concentração não são risco de
sobrepreço ou direcionamento. Por isso todo atributo passa por `clip(lower=0)`: abaixo do
típico vira 0 (normal).

No experimento sem esse corte (desvio absoluto, dos dois lados), 71% dos contratos Alto do
grupo Municipal · Contrato teriam valor por habitante **abaixo** da mediana da categoria.
Com o corte, são 18% (contratos que estão no Alto por outros motivos, como concentração).

### 4.8 Um modelo por grupo

O Isolation Forest chama de atípico o que é **raro no conjunto de treino**. Num modelo
único para todos os contratos:

| Grupo                    | % da base | % do Alto (modelo único) |
|--------------------------|----------:|-------------------------:|
| Municipal · Contrato     | 52,2      | 51,8                     |
| Estadual · Empenho       | 24,1      | 7,3                      |
| Estadual · Contrato      | 16,0      | 27,9                     |
| Federal · Empenho        | 4,5       | 0,4                      |
| Federal · Contrato       | 2,3       | 12,4                     |
| Não se aplica · Contrato | 0,9       | 0,2                      |

Os contratos federais apareceriam 5x mais no Alto do que na base só por serem diferentes
da maioria. Com um modelo por grupo, cada contrato só é comparado com contratos parecidos.

### 4.9 O que ficou de fora, e por quê

| Candidato                                      | Por que não entrou |
|------------------------------------------------|--------------------|
| Categoria como atributo (one-hot)              | O Isolation Forest isolaria as categorias raras: raridade não é risco. A categoria entra como referência de comparação (4.1). |
| Texto do objeto                                | Já é usado para classificar a categoria. |
| `valorGlobal` diferente de `valorInicial` (aditivos) | Só 5% dos contratos, e na publicação os dois costumam ser iguais. Pode ser um atributo futuro. |
| `numeroRetificacao`                            | 3% dos contratos, e indica correção de cadastro, não comportamento de compra. |
| Assinatura depois da publicação                | É inconsistência de datas: vai para os alertas de cadastro. |
| Modalidade (dispensa, inexigibilidade)         | Seria um bom sinal de risco, mas não vem no endpoint de contratos do PNCP. Exigiria cruzar com o endpoint de compras pelo `numeroControlePncpCompra`. |

---

## 5. SHAP: como o painel explica cada contrato

### 5.1 A pergunta que o SHAP responde

"Quanto cada atributo contribuiu para o caminho médio *deste* contrato ser mais curto
(mais atípico) do que o de um contrato qualquer?"

### 5.2 Valores de Shapley

Vêm da teoria dos jogos (Shapley, 1953). Os atributos são os "jogadores", e o "ganho" de
um conjunto S de atributos é `v(S)`, o caminho médio esperado do contrato quando só os
atributos de S são conhecidos. A contribuição do atributo j é a média, sobre todas as
ordens possíveis de revelar os atributos, de quanto o caminho muda quando j é revelado:

```
phi_j = soma, sobre os S que não contêm j, de  |S|! (m - |S| - 1)! / m!  x  [ v(S + j) - v(S) ]
```

Propriedades que fazem dele uma boa explicação:

- **Eficiência:** `v(nenhum) + soma dos phi = v(todos)` = caminho médio do contrato. As
  contribuições "fecham a conta" exatamente.
- **Simetria:** dois atributos com o mesmo efeito recebem a mesma contribuição.
- **Nulidade:** atributo que não muda nada recebe zero.

### 5.3 O que é v(S) numa árvore do Isolation Forest ("tree path dependent")

Para calcular "o caminho esperado conhecendo só os atributos de S", percorre-se a árvore
da raiz às folhas (função `_esperado_por_coalizao`):

- em um nó que corta um atributo **conhecido** (em S), o contrato segue só para o lado em
  que ele de fato cai;
- em um nó que corta um atributo **desconhecido**, o contrato vai para os dois lados, com
  peso proporcional a quantos contratos de treino foram para cada lado.

É a própria árvore dizendo como o atributo desconhecido se distribui, sem precisar de uma
base de referência separada (Lundberg et al., 2020). No fim, `v(S)` = soma, sobre as
folhas, de (probabilidade de chegar na folha x profundidade da folha + c(contratos na
folha)). A média sobre as 300 árvores dá o `v(S)` da floresta.

### 5.4 Exato, não aproximado

Com no máximo 4 atributos há só 2^4 = 16 conjuntos S. A implementação própria
(`shap_isolation_forest`) calcula todos e aplica a fórmula diretamente. Não há
amostragem, então o resultado é exato.

### 5.5 Biblioteca e implementação própria

O projeto usa a biblioteca `shap` (`TreeExplainer`), que resolve o mesmo jogo com o
algoritmo polinomial de Lundberg, mais rápido. A implementação própria é a reserva: entra
se a biblioteca não estiver instalada ou falhar.

- As duas dão o mesmo resultado. Nas duas bases do projeto, a maior diferença foi de 2 x
  10^-13, e todos os textos de motivo saíram idênticos.
- Antes de usar o resultado da biblioteca, `calcular_shap` **confere a eficiência**:
  `valor base + soma das contribuições` tem que ser igual ao caminho médio de cada contrato
  (recuperado do score do sklearn). Se não bater, usa a implementação própria.
- **Sinal:** no Isolation Forest, caminho mais longo = mais normal. A biblioteca devolve
  "positivo = caminho mais longo". O projeto inverte o sinal, então no painel
  **positivo = deixou o contrato mais atípico**.

### 5.6 Exemplo real

Contrato de Chorozinho (20.163 habitantes), categoria Obras e engenharia: construção de
escola de 13 salas (padrão FNDE), R$ 9.575.135,99. Grupo Municipal · Contrato.

| Atributo          | Valor original                              | Entra no modelo | SHAP    | Fatia  |
|-------------------|---------------------------------------------|----------------:|--------:|-------:|
| Concentração      | 26% do valor do órgão, 16,3x a fatia média  | 1,49            | +4,629  | 65,0%  |
| Valor por habitante | R$ 474,89/hab, 58,1x a mediana da categoria | 1,85          | +1,982  | 27,8%  |
| Vigência          | 420 dias, 1,15x a mediana da categoria      | 0,05            | +0,512  | 7,2%   |
| Recorrência       | 1 contrato com o órgão                      | 0               | -0,464  | (fora) |

Conferência:

```
valor base v(nenhum)          = 13,059 cortes  (caminho médio de um contrato "qualquer")
soma dos SHAP                 =  6,659
13,059 - 6,659                =  6,399 cortes  = caminho médio deste contrato
s(x) = 2^(-6,399 / 10,245)    =  0,649         -> percentil 98,3 no grupo -> Alto
```

- **Fatias:** 4,629 / (4,629 + 1,982 + 0,512) = 65,0%, e assim por diante. Só entram as
  contribuições positivas de atributos acima do padrão. A recorrência (SHAP negativo, ter
  um contrato só é normal) puxou para "normal" e fica de fora.
- **Texto mostrado:** "Fornecedor recebe 26% do valor do órgão, 16x a fatia média por
  fornecedor [65%]; Valor por habitante 58,1x a mediana da categoria [28%]". A vigência,
  com 7%, fica fora do texto (só aparecem fatores com pelo menos 10%), mas aparece no
  gráfico de barras do contrato.

### 5.7 Do SHAP para os textos e os gráficos

- **Motivo (`_motivo`):** até 3 atributos com SHAP positivo **e** desvio acima de zero,
  do maior para o menor, com pelo menos 10% da soma das contribuições positivas.
- **"Por que este contrato foi apontado?" (`fatias_shap`):** as mesmas fatias, em barras.
- **"O que mais pesa nos contratos de risco alto" (`fatores_globais`):** primeiro converte
  o SHAP de cada contrato Alto em fatias que somam 100% e depois tira a média. Não soma os
  SHAP brutos porque cada grupo tem o seu modelo, e caminhos de modelos diferentes não são
  comparáveis; as fatias são. Na base inteira: concentração 44,4%, valor 29,7%,
  recorrência 15,9% e vigência 10,0%.
- **Como ler as porcentagens:** são a divisão do "empurrão para atípico" entre os
  atributos. Não são probabilidade de irregularidade.

---

## 6. Problemas encontrados na revisão e o que foi corrigido

| # | Problema | Efeito | Correção |
|---|----------|--------|----------|
| 1 | **Concentração centrada na mediana do grupo** (0,03x a 0,4x), e não em 1x | Fornecedor que recebe **menos** que a fatia média contava como "concentração acima do padrão": 110 contratos Alto/Médio tinham motivos como "Fornecedor recebe 0,0% do valor do órgão, 0x a fatia média". Contratos sem informação (valor neutro 1x) também ganhavam desvio positivo. | Referência fixa em 1x (`_z_robusto(..., centro=0.0)`). Agora: 0 casos. |
| 2 | **Vigência com MAD quase zero** (62% dos contratos têm cerca de 1 ano) | 830 dos 1.108 motivos que citavam vigência eram contratos de 1 ano comum ("Vigência de 365 dias" numa categoria com mediana de 358). Nesses casos, a vigência respondia em média por 35% da explicação. | Log da razão para a mediana da categoria, sem MAD, com tolerância de 10% (`TOLERANCIA_VIGENCIA`). Agora: 240 motivos citam vigência, 6 deles com 1 ano (em categorias de mediana curta, onde 1 ano é 2x o típico). O texto passou a mostrar a razão ("Vigência de 1.826 dias, 5,0x a mediana da categoria"). |
| 3 | **Alienações no total do órgão** | A venda de bens (receita) entrava no denominador da fatia de cada fornecedor. | `_relacao_fornecedor` recebe a base sem as alienações. |
| 4 | **Sinal do SHAP da biblioteca decidido por correlação** | Heurística: não funcionava com um contrato só e dependia da variação dos dados. | Conferência exata da eficiência (base + soma = caminho médio) antes de inverter o sinal. |
| 5 | **`requirements.txt` com `shap==0.42.1`** | Essa versão não tem pacote para Python 3.12+ e foi compilada para numpy 1.x. Uma instalação limpa falharia (ou cairia sempre na implementação própria). O venv do projeto tinha a 0.52.0. | `shap==0.52.0`, a versão testada. |
| 6 | **`config.toml` fora da raiz** (`streamlit/.streamlit/`) | O README manda rodar a partir da raiz e o Streamlit Cloud só lê `.streamlit/config.toml` na raiz: o tema não era aplicado. | Movido para `.streamlit/config.toml`. |

Os totais não mudam (o percentil fixa 5% Alto e 10% Médio por grupo). Dos 1.099 contratos
Alto antes da revisão, 810 (74%) continuam Alto.

---

## 7. Limitações e pontos de atenção

- **Valor por habitante:** ver 4.2. É a principal decisão em aberto.
- **Atípico não é irregular.** O modelo aponta o que foge do padrão. Uma obra grande e
  legítima pode ser atípica. O painel indica onde olhar primeiro.
- **O Alto é sempre 5% de cada grupo**, mesmo numa base sem irregularidades.
- **Depende da classificação.** O valor é comparado com a categoria. Um contrato
  classificado na categoria errada (ex.: uma obra em "Material de expediente") parece
  caro por erro do classificador (acurácia de 92% no holdout).
- **Registro de preços** aumenta a recorrência (4.5).
- **Concentração levemente acima de 1x** ainda pode ganhar peso pelo mecanismo dos nós
  profundos (seção 2): 84 dos 2.796 casos (3%) com desvio menor que 0,1. Bem menor que o
  problema da vigência, por isso não ganhou tolerância.
- **Categorias com menos de 5 contratos** no grupo são comparadas com a mediana do grupo,
  mas o texto continua dizendo "a mediana da categoria".
- **Concentração e recorrência dependem do período carregado:** a mesma base filtrada para
  outro período dá outros números.
- **Site de apresentação** (`site/src/components/sections/DashboardPreview.tsx`): o
  exemplo de motivo "Vigência muito curta" é de uma versão antiga. Hoje vigência curta é
  alerta de cadastro, e o modelo só olha vigência longa.

---

## 8. Referências

- LIU, F. T.; TING, K. M.; ZHOU, Z.-H. Isolation Forest. *IEEE International Conference on
  Data Mining (ICDM)*, 2008.
- LUNDBERG, S. M.; LEE, S.-I. A Unified Approach to Interpreting Model Predictions.
  *Advances in Neural Information Processing Systems (NeurIPS)*, 2017.
- LUNDBERG, S. M. et al. From local explanations to global understanding with explainable
  AI for trees. *Nature Machine Intelligence*, v. 2, p. 56-67, 2020.
- SHAPLEY, L. S. A Value for n-Person Games. In: *Contributions to the Theory of Games II*.
  Princeton University Press, 1953.
- ROUSSEEUW, P. J.; CROUX, C. Alternatives to the Median Absolute Deviation. *Journal of
  the American Statistical Association*, v. 88, n. 424, 1993 (MAD e o fator 1,4826).
