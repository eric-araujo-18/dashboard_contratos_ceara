"""
Detecção de contratos atípicos com Isolation Forest + explicação com SHAP.

Convertido do notebook notebooks/anomalias.ipynb para um módulo .py
normal (mesmo motivo dos demais). A explicação completa, com os números
das bases, está em docs/deteccao_anomalias.md.

Como o Isolation Forest funciona
--------------------------------
O Isolation Forest (Liu, Ting e Zhou, 2008) é não supervisionado: não há
rótulo de "contrato irregular" para aprender. Em vez de modelar o que é
normal, ele mede o quão FÁCIL é isolar cada contrato dos demais:

  - cada árvore recebe uma amostra aleatória de contratos (256 por padrão);
  - em cada nó, sorteia um atributo e um ponto de corte uniforme entre o
    mínimo e o máximo desse atributo no nó, e divide os contratos em dois;
  - repete até cada contrato ficar sozinho (ou até a profundidade máxima).

Um contrato muito diferente dos outros fica sozinho depois de poucos
cortes (caminho curto); um contrato comum, cercado de parecidos, precisa
de muitos cortes (caminho longo). Com h(x) = tamanho do caminho e a média
E[h(x)] nas N_ARVORES árvores, o score é

    s(x) = 2 ** (-E[h(x)] / c(256))    perto de 1 = atípico; bem abaixo de 0,5 = normal

c(n) é o caminho médio numa árvore binária com n pontos (só normaliza).
O sklearn devolve -s(x) em score_samples (maior = mais normal).

Consequência importante para escolher os atributos: o corte é sorteado
entre o mínimo e o máximo, então multiplicar um atributo por uma constante
NÃO muda o resultado. O que muda é (a) transformação não linear (log),
(b) normalização por categoria (cada categoria com seu centro e escala) e
(c) o corte em zero, que define o que conta como "normal".

Decisões de modelagem
---------------------
1. Um modelo por grupo comparável: esfera do órgão (ESFERAS_AVALIADAS:
   municipal, estadual, federal) x tipo de documento (contrato x nota de
   empenho). O Isolation Forest chama de atípico o que é RARO no treino: num
   modelo único, grupos minoritários (ex.: órgãos federais) viravam
   "anômalos" só por serem diferentes da maioria, e empenhos não têm vigência
   comparável à dos contratos. Dentro da esfera municipal, todos os
   municípios entram juntos, então um contrato é comparado com os contratos
   da mesma categoria de todo o estado. Como cada órgão pertence a uma só
   esfera, os grupos não interferem uns nos outros.
2. Fora do modelo ("Não avaliado"):
   - órgãos sem esfera definida no PNCP ("Não se aplica", "Não informada"):
     grupo pequeno e heterogêneo, sem um padrão comum de comparação;
   - alienações (venda de bens pelo governo: é receita, não despesa);
   - grupos com menos de MINIMO_CONTRATOS contratos para comparar.
3. Atributos só com sentido de RISCO (sobrepreço, direcionamento), todos
   "de um lado só": valores abaixo do normal viram 0 (clip) e não contam.
   Sem isso, o Isolation Forest (que é simétrico) também apontaria
   contratos baratos ou curtos demais, que não são risco de sobrepreço.
     - valor:        desvio robusto (mediana/MAD) do log do valor dentro da
                     categoria do contrato. Valor absoluto, sem dividir pela
                     população: o valor do contrato quase não acompanha o
                     porte do município (Spearman 0,065; o contrato mediano
                     de Fortaleza é do tamanho do de uma cidade de 20 mil
                     habitantes), e o valor por habitante empurrava os
                     municípios pequenos para o topo do risco.
     - vigencia:     log da razão entre a duração e a mediana da categoria,
                     contando só o que passar de 10% acima da mediana (só
                     contratos; empenhos valem até 31/12 e não têm vigência
                     comparável). Não divide pela MAD porque quase todos os
                     contratos têm 12 meses e a MAD fica perto de 0.
     - concentracao: fatia do valor do ÓRGÃO COMPRADOR que ficou com o mesmo
                     fornecedor, dividida pela fatia média por fornecedor do
                     órgão. A referência é 1x (fatia igual à média): só conta
                     o fornecedor que recebe MAIS que a média.
     - recorrencia:  quantos contratos o mesmo fornecedor tem com o órgão
                     (desvio robusto em relação ao grupo).
4. Problemas de cadastro (valor simbólico, datas inconsistentes) viram um
   alerta separado ("alertaCadastro"), em vez de se misturarem ao risco.
5. Explicação: valores SHAP calculados com a biblioteca shap
   (shap.TreeExplainer, Lundberg et al., 2020). Se a biblioteca não estiver
   instalada, falhar ou não passar na conferência de aditividade, o módulo
   usa uma implementação própria do TreeSHAP exato ("tree path dependent"),
   que dá o mesmo resultado; assim o app nunca fica sem explicação. O método
   usado fica em info["metodo_shap"].
   Um valor SHAP positivo aqui = o atributo tornou o contrato MAIS atípico.

O índice (0-100) é o percentil de atipicidade DENTRO do grupo:
Alto = 5% mais atípicos, Médio = faixa seguinte de 10%. É uma fila de
prioridade para auditoria, não uma estimativa de quantos contratos são
irregulares.
"""
from __future__ import annotations

from math import factorial

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

try:
    import shap
except Exception:  # biblioteca ausente ou incompatível: usa a implementação própria
    shap = None

MINIMO_CONTRATOS = 50            # por grupo, para o modelo fazer sentido
MINIMO_CONTRATOS_CATEGORIA = 5   # abaixo disso, compara com o grupo inteiro
MINIMO_CONTRATOS_ORGAO = 5       # abaixo disso, concentração não é calculada
PERCENTIL_ALTO = 0.95
PERCENTIL_MEDIO = 0.85
N_ARVORES = 300               # 300 deixa o ranking mais estável entre execuções
SEMENTE = 42                  # mesma base -> mesmo resultado

TOLERANCIA_VIGENCIA = 1.10       # vigência até 10% acima da mediana da categoria = normal

VALOR_SIMBOLICO = 100.0          # contratos até R$ 100 viram alerta de cadastro
ID_ALIENACAO = 11                # categoriaProcesso.id "Alienação de bens móveis/imóveis"
ESFERAS_AVALIADAS = ("Municipal", "Estadual", "Federal")  # "Não se aplica" fica de fora

ATRIBUTOS_ROTULO = {
    "valor": "Valor acima do padrão da categoria",
    "vigencia": "Vigência mais longa que o padrão da categoria",
    "concentracao": "Concentração no mesmo fornecedor",
    "recorrencia": "Muitos contratos com o mesmo fornecedor",
}


# ---------------------------------------------------------------------------
# ATRIBUTOS
# ---------------------------------------------------------------------------

def _z_robusto(
    serie: pd.Series, chaves: pd.Series, centro: float | None = None
) -> tuple[pd.Series, pd.Series]:
    """
    Desvio robusto de cada valor em relação ao seu grupo de chaves:

        z = (x - mediana do grupo) / (1,4826 * MAD do grupo)

    MAD = mediana de |x - mediana|. O fator 1,4826 põe a MAD na escala do
    desvio-padrão (para dados normais), então z = 3 é "3 desvios acima do
    típico".

    Por que mediana/MAD e não média/desvio-padrão: média e desvio-padrão são
    puxados justamente pelos contratos extremos que queremos achar (um
    contrato de R$ 100 milhões infla o desvio-padrão e "esconde" os outros).
    A mediana e a MAD só mudam se mais da metade dos dados mudar.

    Grupos com menos de MINIMO_CONTRATOS_CATEGORIA valores usam a mediana e a
    escala do conjunto todo (não há base para estimar o típico). Grupos com
    MAD zero (mais da metade dos valores idênticos) usam a escala do conjunto.

    centro: se informado, substitui a mediana como ponto de referência (a
    escala continua sendo a MAD). Serve para atributos com uma referência
    natural, como a concentração (1x a fatia média = sem concentração).

    Retorna (z, centro usado em cada linha).
    """
    mediana_geral = serie.median()
    mad_geral = (serie - mediana_geral).abs().median() * 1.4826
    escala_geral = mad_geral if mad_geral > 0 else (serie.std() or 1.0)

    mediana = serie.groupby(chaves).transform("median")
    mad = (serie - mediana).abs().groupby(chaves).transform("median") * 1.4826
    n = serie.groupby(chaves).transform("size")

    pequeno = n < MINIMO_CONTRATOS_CATEGORIA
    mediana = mediana.where(~pequeno, mediana_geral)
    escala = mad.where((mad > 0) & ~pequeno, escala_geral)
    if centro is not None:
        mediana = pd.Series(float(centro), index=serie.index)
    return (serie - mediana) / escala, mediana


def _grupo_modelo(df: pd.DataFrame) -> pd.Series:
    """
    Grupo de comparação de cada contrato: "esfera · documento"
    (ex.: "Municipal · Contrato", "Estadual · Empenho"). Cada grupo tem o seu
    próprio Isolation Forest, então um contrato só concorre com parecidos.
    Só os grupos das ESFERAS_AVALIADAS são avaliados.
    """
    esfera = df.get("esfera", pd.Series("Não informada", index=df.index)).fillna("Não informada")
    tipo = df.get("tipoContrato.nome", pd.Series("", index=df.index)).fillna("")
    # o PNCP tem vários tipos (Contrato (termo inicial), Empenho, Termo de
    # Adesão, Carta Contrato...); só o Empenho é estruturalmente diferente
    # (sem vigência comparável), os demais entram juntos como "Contrato"
    documento = np.where(tipo.eq("Empenho"), "Empenho", "Contrato")
    return esfera + " · " + documento


def _duracao_dias(df: pd.DataFrame) -> pd.Series:
    """Vigência em dias (fim - início). NaN quando as datas não existem."""
    if {"dataVigenciaInicio", "dataVigenciaFim"} <= set(df.columns):
        return (df["dataVigenciaFim"] - df["dataVigenciaInicio"]).dt.days
    return pd.Series(np.nan, index=df.index)


def _relacao_fornecedor(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Para cada contrato, olhando o par órgão comprador x fornecedor:
      - fatia: parte do valor total do órgão que ficou com o fornecedor;
      - vezes_media: essa fatia dividida pela fatia média de um fornecedor do
        órgão (1 / nº de fornecedores). Assim 7% num órgão com 300
        fornecedores (21x a média) pesa mais que 30% num órgão com 3 (0,9x);
      - n_contratos: quantos contratos o fornecedor tem com o órgão.

    Contratos sem base para o cálculo (órgão com menos de
    MINIMO_CONTRATOS_ORGAO contratos ou fornecedor sem CNPJ/CPF) recebem os
    valores neutros: fatia 0, vezes_media 1 (exatamente a média) e
    n_contratos 1.

    Limitação conhecida: um órgão que comprou tudo de um único fornecedor tem
    vezes_media = 1 (ele É a média). Esse caso aparece pela recorrência
    (muitos contratos com o mesmo fornecedor), não pela concentração.
    """
    valor = df["valor"].astype(float)
    orgao = (df["orgaoEntidade.cnpj"] if "orgaoEntidade.cnpj" in df.columns else df["municipio"]).astype(str)
    forn = df["niFornecedor"].fillna("").astype(str) if "niFornecedor" in df.columns else pd.Series("", index=df.index)

    total_orgao = valor.groupby(orgao).transform("sum")              # quanto o órgão contratou
    n_orgao = valor.groupby(orgao).transform("size")                 # quantos contratos o órgão tem
    n_fornecedores = forn.groupby(orgao).transform("nunique")        # com quantos fornecedores
    total_par = valor.groupby([orgao, forn]).transform("sum")        # quanto foi para ESTE fornecedor
    n_par = valor.groupby([orgao, forn]).transform("size")           # em quantos contratos

    identificado = forn != ""
    valido = (n_orgao >= MINIMO_CONTRATOS_ORGAO) & identificado
    fatia = (total_par / total_orgao).where(valido, 0.0).fillna(0.0)
    vezes_media = (fatia * n_fornecedores).where(valido, 1.0).fillna(1.0)
    n_contratos = n_par.where(identificado, 1)
    return fatia, vezes_media, n_contratos


def alertas_cadastro(df: pd.DataFrame) -> pd.Series:
    """
    Problemas de cadastro, separados do risco: costumam ser erro de
    preenchimento, e não comportamento do comprador. Se entrassem no modelo,
    dominariam o topo do ranking (são os pontos mais fáceis de isolar).
    Retorna, para cada contrato, os alertas separados por "; " ("" = nenhum).
    """
    duracao = _duracao_dias(df)
    tipo = df.get("tipoContrato.nome", pd.Series("", index=df.index)).fillna("")
    alertas = pd.Series([[] for _ in range(len(df))], index=df.index)

    def marcar(mascara, texto):
        for i in df.index[mascara.fillna(False)]:
            alertas[i].append(texto)

    marcar(df["valor"] <= VALOR_SIMBOLICO, f"Valor simbólico (até R$ {VALOR_SIMBOLICO:.0f})")
    marcar(duracao < 0, "Vigência termina antes de começar")
    marcar((duracao <= 1) & tipo.ne("Empenho"), "Contrato com vigência de até 1 dia")
    if {"dataAssinatura", "dataPublicacaoPncp"} <= set(df.columns):
        # compara só o dia: a publicação tem hora, a assinatura não
        apos = df["dataAssinatura"] > df["dataPublicacaoPncp"].dt.normalize()
        marcar(apos, "Assinatura posterior à publicação no PNCP")
    return alertas.map("; ".join)


# ---------------------------------------------------------------------------
# SHAP EXATO PARA ISOLATION FOREST
#
# O que o SHAP responde: "quanto cada atributo contribuiu para o caminho
# médio deste contrato ser mais curto (mais atípico) do que o de um contrato
# qualquer?". Vem da teoria dos jogos (valores de Shapley): os atributos são
# "jogadores", e v(S) é o caminho médio esperado quando só os atributos do
# conjunto S são conhecidos. A contribuição de um atributo j é a média,
# sobre todas as ordens possíveis de revelar os atributos, de quanto o
# caminho muda quando j é revelado:
#
#   phi_j = soma sobre S sem j de  |S|! (m-|S|-1)! / m!  * [v(S ∪ {j}) - v(S)]
#
# Propriedade usada para conferir o cálculo (eficiência):
#   v(nenhum atributo) + soma(phi) = v(todos) = caminho médio do contrato.
#
# Com no máximo 4 atributos há só 2**4 = 16 conjuntos S, então dá para
# calcular TODOS e obter o valor exato, sem aproximação por amostragem.
# ---------------------------------------------------------------------------

def _comprimento_medio(n: np.ndarray) -> np.ndarray:
    """
    c(n): profundidade média de uma busca malsucedida numa árvore binária de
    busca com n pontos (Liu et al., 2008):
        c(n) = 2 (ln(n-1) + 0,5772...) - 2 (n-1)/n,  c(2) = 1,  c(1) = c(0) = 0.
    Usado (1) para normalizar o score e (2) para estimar quantos cortes ainda
    faltariam numa folha que parou com vários contratos juntos.
    """
    n = np.asarray(n, dtype=float)
    saida = np.zeros_like(n)
    saida[n == 2] = 1.0
    grande = n > 2
    saida[grande] = 2.0 * (np.log(n[grande] - 1.0) + np.euler_gamma) - 2.0 * (n[grande] - 1.0) / n[grande]
    return saida


def _valor_folhas(arvore) -> np.ndarray:
    """
    "Saída" de cada nó da árvore, no sentido do Isolation Forest:
    profundidade do nó + c(nº de amostras de treino no nó).

    As árvores do Isolation Forest param na profundidade ceil(log2(256)) = 8,
    então uma folha pode ter vários contratos que não chegaram a ser
    separados; c(n) estima quantos cortes ainda faltariam. É exatamente o
    h(x) que o sklearn usa no score. Só os valores das folhas são usados.
    """
    t = arvore.tree_
    profundidade = np.zeros(t.node_count)
    for no in range(t.node_count):  # os filhos sempre têm índice maior que o pai
        if t.children_left[no] != -1:
            profundidade[t.children_left[no]] = profundidade[no] + 1
            profundidade[t.children_right[no]] = profundidade[no] + 1
    return profundidade + _comprimento_medio(t.n_node_samples)


def _esperado_por_coalizao(arvore, X: np.ndarray, mascaras: np.ndarray, folhas: np.ndarray) -> np.ndarray:
    """
    v(S) = E[caminho | atributos de S conhecidos] numa árvore, para todas as
    coalizões S (linhas de `mascaras`) e todos os contratos (linhas de X) de
    uma vez. Retorna uma matriz [coalizões, contratos].

    Percorre a árvore da raiz às folhas carregando, para cada nó, a
    probabilidade de o contrato chegar até ele (`pesos`):
      - nó que corta um atributo CONHECIDO (em S): o contrato vai só para o
        lado em que ele de fato cai (peso 1 de um lado, 0 do outro);
      - nó que corta um atributo DESCONHECIDO: o contrato "vai para os dois
        lados", com peso proporcional a quantos contratos de treino foram
        para cada lado. É a própria árvore dizendo como esse atributo se
        distribui ("tree path dependent", Lundberg et al., 2020), sem
        precisar de uma base de referência separada.
    No fim, v(S) = soma sobre as folhas de (peso da folha x valor da folha).
    """
    t = arvore.tree_
    esq, dir_, atributo = t.children_left, t.children_right, t.feature
    limiar, amostras = t.threshold, t.n_node_samples

    saida = np.zeros((mascaras.shape[0], X.shape[0]))
    pesos = {0: np.ones_like(saida)}  # raiz: todo contrato passa por ela
    for no in range(t.node_count):    # pais antes dos filhos (ordem do sklearn)
        w = pesos.pop(no)
        if esq[no] == -1:              # folha: acumula a contribuição dela
            saida += w * folhas[no]
            continue
        f = atributo[no]
        vai_esquerda = X[:, f] <= limiar[no]
        fracao = amostras[esq[no]] / amostras[no]   # fração do treino que foi para a esquerda
        conhecido = mascaras[:, f][:, None]
        pesos[esq[no]] = w * np.where(conhecido, vai_esquerda[None, :], fracao)
        pesos[dir_[no]] = w * np.where(conhecido, ~vai_esquerda[None, :], 1.0 - fracao)
    return saida


def shap_isolation_forest(modelo: IsolationForest, X: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Valores SHAP exatos do tamanho médio do caminho, com o sinal invertido
    (positivo = deixa o contrato MAIS atípico). Retorna (shap[n, m], valor_base).
    Propriedade garantida: valor_base - soma(shap) = caminho médio do contrato.

    Passos:
      1. monta as 2**m coalizões como máscaras de bits (coalizão c contém o
         atributo j se o bit j de c for 1);
      2. calcula v(S) em cada árvore e tira a média da floresta (o SHAP de
         uma média de modelos é a média dos SHAP de cada modelo);
      3. aplica a fórmula de Shapley para cada atributo.
    """
    X = np.asarray(X, dtype=np.float32)  # as árvores do sklearn comparam em float32
    n, m = X.shape
    k = 1 << m
    mascaras = np.array([[(c >> j) & 1 for j in range(m)] for c in range(k)], dtype=bool)

    # v[c, i] = caminho médio esperado do contrato i conhecendo só a coalizão c
    v = np.zeros((k, n))
    for arvore, atributos in zip(modelo.estimators_, modelo.estimators_features_):
        v += _esperado_por_coalizao(arvore, X[:, atributos], mascaras[:, atributos], _valor_folhas(arvore))
    v /= len(modelo.estimators_)

    # phi_j = soma ponderada das contribuições marginais de j em cada coalizão sem j
    phi = np.zeros((n, m))
    tamanho = mascaras.sum(axis=1)
    for j in range(m):
        sem_j = ~mascaras[:, j]
        for c in np.flatnonzero(sem_j):
            s = tamanho[c]
            peso = factorial(s) * factorial(m - s - 1) / factorial(m)
            phi[:, j] += peso * (v[c | (1 << j)] - v[c])

    # phi > 0 = caminho mais LONGO = mais normal; o painel mostra o contrário.
    # v[0] (nenhum atributo conhecido) é igual para todos os contratos.
    return -phi, float(v[0].mean())


def _caminho_medio(modelo: IsolationForest, X: np.ndarray) -> np.ndarray:
    """
    E[h(x)] de cada contrato, recuperado do score do sklearn:
    score_samples = -2 ** (-E[h(x)] / c(max_samples))
    =>  E[h(x)] = -log2(-score_samples) * c(max_samples).
    """
    c = _comprimento_medio(np.array([modelo.max_samples_]))[0]
    return -np.log2(-modelo.score_samples(X)) * c


METODO_BIBLIOTECA = "biblioteca shap (TreeExplainer)"
METODO_PROPRIO = "TreeSHAP exato (implementação própria)"


def calcular_shap(modelo: IsolationForest, X: np.ndarray) -> tuple[np.ndarray, str]:
    """
    Contribuições SHAP de cada atributo, com o sinal "positivo = mais atípico".
    Retorna (valores[n, m], método usado).

    A biblioteca shap (TreeExplainer) explica o caminho médio E[h(x)] do
    Isolation Forest, com o mesmo jogo "tree path dependent" da implementação
    própria, mas pelo algoritmo polinomial de Lundberg (mais rápido). As duas
    dão o mesmo resultado (diferença da ordem de 1e-14 nas bases testadas).
    """
    if shap is not None:
        try:
            explicador = shap.TreeExplainer(modelo)
            valores = np.asarray(explicador.shap_values(X), dtype=float)
            base = float(np.ravel(explicador.expected_value)[0])
            # Confere a eficiência (base + soma das contribuições = caminho
            # médio de cada contrato) antes de inverter o sinal: caminho mais
            # longo = mais normal, e o painel mostra "positivo = mais atípico".
            # Se a conferência falhar (ex.: versão da biblioteca que explique
            # outra saída), usa a implementação própria.
            if valores.shape == X.shape and np.allclose(
                base + valores.sum(axis=1), _caminho_medio(modelo, X), atol=1e-3
            ):
                return -valores, METODO_BIBLIOTECA
        except Exception:
            pass
    valores, _ = shap_isolation_forest(modelo, X)
    return valores, METODO_PROPRIO


# ---------------------------------------------------------------------------
# MOTIVOS (a partir do SHAP)
# ---------------------------------------------------------------------------

def _num(valor: float, casas: int = 1) -> str:
    """Número no formato brasileiro: 1.234,5"""
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(fracao: float) -> str:
    """Fração como porcentagem (0,07 -> "7%"); abaixo de 1% mostra uma casa."""
    return f"{_num(fracao * 100, 1 if fracao < 0.01 else 0)}%"


def _descrever(atributo: str, linha: pd.Series) -> str:
    """
    Frase com o valor ORIGINAL do atributo (não o desvio robusto), para quem
    lê o painel: "Valor 12,3x a mediana da categoria", "Vigência de 730 dias".
    As colunas com "_" na frente são montadas em detectar_anomalias.
    """
    if atributo == "valor":
        return f"Valor {_num(linha['_razao'])}x a mediana da categoria"
    if atributo == "vigencia":
        return (
            f"Vigência de {_num(linha['_duracao'], 0)} dias, "
            f"{_num(linha['_razao_vigencia'])}x a mediana da categoria"
        )
    if atributo == "concentracao":
        vezes = linha["_vezes_media"]
        return (
            f"Fornecedor recebe {_pct(linha['_fatia'])} do valor do órgão, "
            f"{_num(vezes, 1 if vezes < 10 else 0)}x a fatia média por fornecedor"
        )
    if atributo == "recorrencia":
        return f"Fornecedor com {_num(linha['_n_contratos'], 0)} contratos no órgão"
    return ATRIBUTOS_ROTULO.get(atributo, atributo)


def _motivo(linha: pd.Series, atributos: list[str]) -> str:
    """
    Texto da coluna "Principais fatores (SHAP)": até 3 atributos, do que mais
    empurrou o contrato para atípico ao que menos, com a fatia de cada um
    entre colchetes. A fatia é a contribuição SHAP do atributo dividida pela
    soma das contribuições positivas (as que empurram para atípico); os
    atributos que puxaram para normal (SHAP negativo) ficam de fora.
    Fatores com menos de 10% só aparecem se forem o único.
    """
    # só atributos que estão de fato ACIMA do padrão (desvio > 0) e empurram
    # para atípico (SHAP > 0). Um atributo no piso (desvio 0) pode ter SHAP
    # levemente positivo por interação com os outros, mas não é um "motivo".
    contribuicoes = {
        a: linha[f"shap_{a}"] for a in atributos
        if linha[f"shap_{a}"] > 0 and linha[f"desvio_{a}"] > 0
    }
    total = sum(contribuicoes.values())
    if total <= 0:
        return "Combinação atípica de atributos"
    partes = []
    for atributo, valor in sorted(contribuicoes.items(), key=lambda kv: -kv[1])[:3]:
        fatia = valor / total
        if fatia >= 0.10 or not partes:
            partes.append(f"{_descrever(atributo, linha)} [{_pct(fatia)}]")
    return "; ".join(partes)


# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------

def detectar_anomalias(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Roda a detecção em todos os grupos e devolve (df com as colunas de risco,
    info com o resumo). Colunas criadas:
      scoreIF        s(x) do Isolation Forest (maior = mais atípico)
      scoreRisco     percentil de s(x) dentro do grupo, 0-100
      risco          Alto / Médio / Baixo / Não avaliado
      motivoRisco    texto com os principais fatores (SHAP) ou o motivo de não avaliar
      grupoModelo    grupo de comparação
      alertaCadastro erros de cadastro (fora do risco)
      desvio_<attr>  valor do atributo que entrou no modelo (>= 0; 0 = no padrão ou abaixo)
      shap_<attr>    contribuição SHAP do atributo (só Alto e Médio)
    """
    df = df.copy()
    df["scoreRisco"] = 0.0
    df["scoreIF"] = np.nan
    df["risco"] = "Não avaliado"
    df["motivoRisco"] = ""
    df["grupoModelo"] = _grupo_modelo(df)
    df["alertaCadastro"] = alertas_cadastro(df)
    for atributo in ATRIBUTOS_ROTULO:
        df[f"shap_{atributo}"] = np.nan    # contribuição SHAP (só Alto e Médio)
        df[f"desvio_{atributo}"] = np.nan  # valor do atributo usado no modelo (>= 0)

    esfera = df.get("esfera", pd.Series("Não informada", index=df.index)).fillna("Não informada")
    fora_escopo = ~esfera.isin(ESFERAS_AVALIADAS)
    df.loc[fora_escopo, "motivoRisco"] = (
        "Fora do escopo: órgão sem esfera definida no PNCP (" + esfera[fora_escopo] + ")"
    )

    categoria_proc = pd.to_numeric(df.get("categoriaProcesso.id", pd.Series(np.nan, index=df.index)), errors="coerce")
    alienacao = categoria_proc.eq(ID_ALIENACAO)
    df.loc[alienacao, "motivoRisco"] = "Alienação: venda de bens pelo governo (receita, não despesa)"

    avaliavel = ~fora_escopo & ~alienacao
    info_base = {"fora_escopo": int((fora_escopo & ~alienacao).sum()), "alienacoes": int(alienacao.sum())}
    if avaliavel.sum() < MINIMO_CONTRATOS:
        return df, {
            "aplicado": False,
            "motivo": f"São necessários ao menos {MINIMO_CONTRATOS} contratos de órgãos municipais, estaduais ou federais.",
            **info_base,
        }

    # A relação órgão x fornecedor olha todos os contratos avaliáveis (contratos
    # e empenhos), mas sem as alienações: elas são receita e inflariam o
    # "total do órgão". Cada órgão pertence a uma só esfera, então o recorte
    # de escopo não muda as contas de nenhum órgão municipal.
    fatia_forn, vezes_media_forn, n_contratos_forn = _relacao_fornecedor(df.loc[avaliavel])
    duracao = _duracao_dias(df)

    grupos_info = {}
    metodos_shap: set[str] = set()
    for grupo, idx in df.index[avaliavel].groupby(df.loc[avaliavel, "grupoModelo"]).items():
        sub = df.loc[idx]
        if len(sub) < MINIMO_CONTRATOS:
            df.loc[idx, "motivoRisco"] = "Grupo com poucos contratos para comparação"
            grupos_info[grupo] = {"contratos": len(sub), "avaliado": False}
            continue

        empenho = grupo.endswith("Empenho")
        categoria = sub["categoria"]

        # --- valor ---
        # Log porque os valores vão de centenas de reais a centenas de milhões:
        # na escala original, um único contrato gigante ocuparia quase todo o
        # intervalo [mínimo, máximo] e os cortes aleatórios do Isolation Forest
        # quase nunca separariam os contratos "só" 10x acima do típico. No log,
        # 10x acima é a mesma distância em qualquer faixa de valor.
        # Valor absoluto, sem dividir pela população (ver docstring do módulo).
        log_valor = np.log(sub["valor"].astype(float).clip(lower=1.0))
        # Comparado com a CATEGORIA do contrato: uma obra é naturalmente mais
        # cara que material de expediente; sem isso, toda obra seria "atípica"
        z_valor, mediana_valor = _z_robusto(log_valor, categoria)

        atributos = ["valor"]
        # clip(lower=0): abaixo do típico vira 0 = "normal" (só um lado é risco)
        colunas = {"valor": z_valor.clip(lower=0)}

        # --- vigência (só contratos) ---
        # Empenhos ficam de fora: 98% deles terminam em 31/12 (valem até o fim
        # do exercício), então a "vigência" só mede a data de emissão.
        razao_vigencia = None
        if not empenho:
            dur = duracao.loc[idx]
            # sem datas: usa a mediana do grupo (fica neutro, desvio ~0)
            log_dur = np.log1p(dur.clip(lower=0).fillna(dur.median() if dur.notna().any() else 0))
            # Razão para a mediana da categoria (em log), SEM dividir pela MAD
            # e com tolerância de 10%. A vigência é muito concentrada em 12
            # meses (62% dos contratos entre 360 e 366 dias):
            #   - a MAD da categoria fica perto de zero, e 365 dias numa
            #     categoria com mediana 358 virava um desvio de 0,67. Com o
            #     desvio robusto, 830 dos 1.108 motivos que citavam vigência
            #     eram contratos de 1 ano comum (35% da explicação, em média);
            #   - mesmo sem a MAD, 365/358 dá um valor pequeno mas maior que
            #     zero, e o Isolation Forest separa qualquer valor diferente
            #     nos nós mais fundos (o corte é sorteado entre o mínimo e o
            #     máximo DO NÓ).
            # Com a tolerância, até 10% acima da mediana (ex.: 12 meses numa
            # categoria cujo típico é 11) conta como normal (0); o dobro da
            # mediana dá log(2) - log(1,1) = 0,6.
            _, mediana_dur = _z_robusto(log_dur, categoria)
            atributos.append("vigencia")
            colunas["vigencia"] = (log_dur - mediana_dur - np.log(TOLERANCIA_VIGENCIA)).clip(lower=0)
            razao_vigencia = np.exp(log_dur - mediana_dur)

        # --- relação com o fornecedor (comparada com o próprio grupo) ---
        mesmo_grupo = pd.Series(0, index=idx)
        # Concentração: a referência é 1x a fatia média (log 1 = 0), e não a
        # mediana do grupo. A mediana fica bem abaixo de 1x (de 0,03x a 0,4x
        # nas bases testadas), porque em cada órgão poucos fornecedores ficam
        # com quase todo o valor e a maioria recebe pouco. Centrado na mediana,
        # um fornecedor com 0,3x a fatia média (MENOS que a média) contava como
        # "concentração acima do padrão", e os contratos sem informação (valor
        # neutro 1x) também. Com o centro em 1x, desvio > 0 significa
        # exatamente "o fornecedor recebe mais que a fatia média do órgão".
        z_conc, _ = _z_robusto(np.log(vezes_media_forn.loc[idx].clip(lower=1e-6)), mesmo_grupo, centro=0.0)
        # Recorrência: não há uma referência natural, então o típico é a
        # mediana do grupo. log1p porque 1 -> 2 contratos importa mais que 40 -> 41.
        z_rec, _ = _z_robusto(np.log1p(n_contratos_forn.loc[idx]), mesmo_grupo)
        atributos += ["concentracao", "recorrencia"]
        colunas["concentracao"] = z_conc.clip(lower=0)
        colunas["recorrencia"] = z_rec.clip(lower=0)

        # matriz de atributos [contratos, atributos], todos >= 0
        X = np.nan_to_num(pd.DataFrame(colunas)[atributos].to_numpy(dtype=float))
        for j, atributo in enumerate(atributos):
            df.loc[idx, f"desvio_{atributo}"] = X[:, j]

        # Sem `contamination`: o modelo só produz o score; o corte em Alto /
        # Médio é feito pelo percentil logo abaixo
        modelo = IsolationForest(n_estimators=N_ARVORES, random_state=SEMENTE, n_jobs=-1)
        modelo.fit(X)
        score = pd.Series(-modelo.score_samples(X), index=idx)  # s(x): maior = mais atípico
        # O score absoluto não é comparável entre modelos diferentes; o
        # percentil dentro do grupo é (5% mais atípicos de cada grupo = Alto)
        percentil = score.rank(pct=True, method="average")

        df.loc[idx, "scoreIF"] = score
        df.loc[idx, "scoreRisco"] = (percentil * 100).round(1)
        df.loc[idx, "risco"] = np.select(
            [percentil >= PERCENTIL_ALTO, percentil >= PERCENTIL_MEDIO], ["Alto", "Médio"], "Baixo"
        )

        # --- SHAP para os sinalizados (Alto e Médio) ---
        # Só eles aparecem no painel; o modelo continua sendo o do grupo todo
        sinalizado = (percentil >= PERCENTIL_MEDIO).to_numpy()
        if sinalizado.any():
            valores_shap, metodo = calcular_shap(modelo, X[sinalizado])
            metodos_shap.add(metodo)
            idx_sinal = idx[sinalizado]
            for j, atributo in enumerate(atributos):
                df.loc[idx_sinal, f"shap_{atributo}"] = valores_shap[:, j]

            # valores originais, para o texto do motivo ficar legível
            apoio = df.loc[idx_sinal, [f"shap_{a}" for a in atributos] + [f"desvio_{a}" for a in atributos]].copy()
            # razão para a mediana da categoria (nas categorias com menos de 5
            # contratos, a referência é a mediana do grupo)
            apoio["_razao"] = np.exp((log_valor - mediana_valor).loc[idx_sinal])
            apoio["_duracao"] = duracao.loc[idx_sinal].fillna(0)
            if razao_vigencia is not None:
                apoio["_razao_vigencia"] = razao_vigencia.loc[idx_sinal]
            apoio["_fatia"] = fatia_forn.loc[idx_sinal]
            apoio["_vezes_media"] = vezes_media_forn.loc[idx_sinal]
            apoio["_n_contratos"] = n_contratos_forn.loc[idx_sinal]
            df.loc[idx_sinal, "motivoRisco"] = apoio.apply(_motivo, axis=1, atributos=atributos)

        grupos_info[grupo] = {
            "contratos": len(sub),
            "avaliado": True,
            "atributos": atributos,
        }

    info = {
        "aplicado": True,
        "n_contratos": len(df),
        "avaliados": int((df["risco"] != "Não avaliado").sum()),
        "nao_avaliados": int((df["risco"] == "Não avaliado").sum()),
        "alto": int((df["risco"] == "Alto").sum()),
        "medio": int((df["risco"] == "Médio").sum()),
        "alertas_cadastro": int((df["alertaCadastro"] != "").sum()),
        **info_base,
        "grupos": grupos_info,
        "metodo_shap": " + ".join(sorted(metodos_shap)) if metodos_shap else None,
    }
    return df, info
