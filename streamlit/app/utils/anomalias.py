"""
Detecção de contratos atípicos com Isolation Forest + explicação com SHAP.

Convertido do notebook notebooks/anomalias.ipynb para um módulo .py
normal (mesmo motivo dos demais).

Decisões de modelagem
---------------------
1. Um modelo por grupo comparável (esfera do órgão x tipo de documento).
   Contratos municipais, estaduais e federais, e empenhos x contratos, têm
   naturezas diferentes; num modelo único, grupos minoritários (ex.: órgãos
   federais) viravam "anômalos" só por serem diferentes da maioria.
2. Fora do modelo:
   - alienações (venda de bens pelo governo: é receita, não despesa);
   - grupos com poucos contratos para comparar.
   Esses contratos ficam como "Não avaliado".
3. Atributos só com sentido de RISCO (sobrepreço, direcionamento), todos
   "de um lado só": valores abaixo do normal não contam como risco.
     - valor:        desvio robusto (mediana/MAD) do log do valor dentro da
                     categoria do contrato. Nos municipais, usa o valor POR
                     HABITANTE (IBGE), para comparar municípios de tamanhos
                     diferentes.
     - vigencia:     desvio robusto da duração dentro da categoria
                     (só contratos; empenhos não têm vigência comparável).
     - concentracao: fatia do valor do ÓRGÃO COMPRADOR que ficou com o mesmo
                     fornecedor, dividida pela fatia média por fornecedor do
                     órgão (desvio robusto em relação ao grupo).
     - recorrencia:  quantos contratos o mesmo fornecedor tem com o órgão
                     (desvio robusto em relação ao grupo).
4. Problemas de cadastro (valor simbólico, datas inconsistentes) viram um
   alerta separado ("alertaCadastro"), em vez de se misturarem ao risco.
5. Explicação: valores SHAP calculados com a biblioteca shap
   (shap.TreeExplainer, Lundberg et al., 2020). Se a biblioteca não estiver
   instalada ou falhar, o módulo usa uma implementação própria do TreeSHAP
   exato ("tree path dependent"), que dá o mesmo resultado; assim o app
   nunca fica sem explicação. O método usado fica em info["metodo_shap"].
   Um valor SHAP positivo aqui = o atributo tornou o contrato MAIS atípico.

O índice (0-100) é o percentil de atipicidade DENTRO do grupo:
Alto = 5% mais atípicos, Médio = faixa seguinte de 10%.
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
SEMENTE = 42

VALOR_SIMBOLICO = 100.0          # contratos até R$ 100 viram alerta de cadastro
ALIENACAO = "Alienação"          # prefixo de categoriaProcesso.nome

ATRIBUTOS_ROTULO = {
    "valor": "Valor acima do padrão da categoria",
    "valor_habitante": "Valor por habitante acima do padrão da categoria",
    "vigencia": "Vigência mais longa que o padrão da categoria",
    "concentracao": "Concentração no mesmo fornecedor",
    "recorrencia": "Muitos contratos com o mesmo fornecedor",
}


# ---------------------------------------------------------------------------
# ATRIBUTOS
# ---------------------------------------------------------------------------

def _z_robusto(serie: pd.Series, chaves: pd.Series) -> tuple[pd.Series, pd.Series]:
    """(z robusto por grupo de chaves, mediana usada). Grupos pequenos usam o conjunto todo."""
    mediana_geral = serie.median()
    mad_geral = (serie - mediana_geral).abs().median() * 1.4826
    escala_geral = mad_geral if mad_geral > 0 else (serie.std() or 1.0)

    mediana = serie.groupby(chaves).transform("median")
    mad = (serie - mediana).abs().groupby(chaves).transform("median") * 1.4826
    n = serie.groupby(chaves).transform("size")

    pequeno = n < MINIMO_CONTRATOS_CATEGORIA
    mediana = mediana.where(~pequeno, mediana_geral)
    escala = mad.where((mad > 0) & ~pequeno, escala_geral)
    return (serie - mediana) / escala, mediana


def _grupo_modelo(df: pd.DataFrame) -> pd.Series:
    esfera = df.get("esfera", pd.Series("Não informada", index=df.index)).fillna("Não informada")
    tipo = df.get("tipoContrato.nome", pd.Series("", index=df.index)).fillna("")
    documento = np.where(tipo.eq("Empenho"), "Empenho", "Contrato")
    return esfera + " · " + documento


def _duracao_dias(df: pd.DataFrame) -> pd.Series:
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
    """
    valor = df["valor"].astype(float)
    orgao = df.get("orgaoEntidade.cnpj", df["municipioNorm"]).astype(str)
    forn = df["niFornecedor"].fillna("").astype(str) if "niFornecedor" in df.columns else pd.Series("", index=df.index)

    total_orgao = valor.groupby(orgao).transform("sum")
    n_orgao = valor.groupby(orgao).transform("size")
    n_fornecedores = forn.groupby(orgao).transform("nunique")
    total_par = valor.groupby([orgao, forn]).transform("sum")
    n_par = valor.groupby([orgao, forn]).transform("size")

    identificado = forn != ""
    valido = (n_orgao >= MINIMO_CONTRATOS_ORGAO) & identificado
    fatia = (total_par / total_orgao).where(valido, 0.0).fillna(0.0)
    vezes_media = (fatia * n_fornecedores).where(valido, 1.0).fillna(1.0)
    n_contratos = n_par.where(identificado, 1)
    return fatia, vezes_media, n_contratos


def alertas_cadastro(df: pd.DataFrame) -> pd.Series:
    """Problemas de cadastro, separados do risco."""
    duracao = _duracao_dias(df)
    tipo = df.get("tipoContrato.nome", pd.Series("", index=df.index)).fillna("")
    alertas = pd.Series([[] for _ in range(len(df))], index=df.index)

    def marcar(mascara, texto):
        for i in df.index[mascara.fillna(False)]:
            alertas[i].append(texto)

    marcar(df["valor"] <= VALOR_SIMBOLICO, f"Valor simbólico (até R$ {VALOR_SIMBOLICO:.0f})")
    marcar(duracao < 0, "Vigência termina antes de começar")
    marcar((duracao <= 1) & tipo.ne("Empenho"), "Contrato com vigência de até 1 dia")
    if "assinaturaAposPublicacao" in df.columns:
        marcar(df["assinaturaAposPublicacao"].astype(bool), "Assinatura posterior à publicação no PNCP")
    return alertas.map("; ".join)


# ---------------------------------------------------------------------------
# SHAP EXATO PARA ISOLATION FOREST
# ---------------------------------------------------------------------------

def _comprimento_medio(n: np.ndarray) -> np.ndarray:
    """c(n): profundidade média de uma busca malsucedida numa árvore binária (Liu et al., 2008)."""
    n = np.asarray(n, dtype=float)
    saida = np.zeros_like(n)
    saida[n == 2] = 1.0
    grande = n > 2
    saida[grande] = 2.0 * (np.log(n[grande] - 1.0) + np.euler_gamma) - 2.0 * (n[grande] - 1.0) / n[grande]
    return saida


def _valor_folhas(arvore) -> np.ndarray:
    """Profundidade de cada nó + c(amostras na folha): o 'tamanho do caminho' do Isolation Forest."""
    t = arvore.tree_
    profundidade = np.zeros(t.node_count)
    for no in range(t.node_count):  # os filhos sempre têm índice maior que o pai
        if t.children_left[no] != -1:
            profundidade[t.children_left[no]] = profundidade[no] + 1
            profundidade[t.children_right[no]] = profundidade[no] + 1
    return profundidade + _comprimento_medio(t.n_node_samples)


def _esperado_por_coalizao(arvore, X: np.ndarray, mascaras: np.ndarray, folhas: np.ndarray) -> np.ndarray:
    """
    E[caminho | atributos da coalizão conhecidos], para todas as coalizões de
    uma vez. Atributo conhecido: segue o lado do contrato. Desconhecido: média
    dos dois lados ponderada pelas amostras de treino (TreeSHAP path dependent).
    """
    t = arvore.tree_
    esq, dir_, atributo = t.children_left, t.children_right, t.feature
    limiar, amostras = t.threshold, t.n_node_samples

    saida = np.zeros((mascaras.shape[0], X.shape[0]))
    pesos = {0: np.ones_like(saida)}
    for no in range(t.node_count):
        w = pesos.pop(no)
        if esq[no] == -1:
            saida += w * folhas[no]
            continue
        f = atributo[no]
        vai_esquerda = X[:, f] <= limiar[no]
        fracao = amostras[esq[no]] / amostras[no]
        conhecido = mascaras[:, f][:, None]
        pesos[esq[no]] = w * np.where(conhecido, vai_esquerda[None, :], fracao)
        pesos[dir_[no]] = w * np.where(conhecido, ~vai_esquerda[None, :], 1.0 - fracao)
    return saida


def shap_isolation_forest(modelo: IsolationForest, X: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Valores SHAP exatos do tamanho médio do caminho, com o sinal invertido
    (positivo = deixa o contrato MAIS atípico). Retorna (shap[n, m], valor_base).
    Propriedade garantida: valor_base - soma(shap) = caminho médio do contrato.
    """
    X = np.asarray(X, dtype=np.float32)  # as árvores do sklearn comparam em float32
    n, m = X.shape
    k = 1 << m
    mascaras = np.array([[(c >> j) & 1 for j in range(m)] for c in range(k)], dtype=bool)

    v = np.zeros((k, n))
    for arvore, atributos in zip(modelo.estimators_, modelo.estimators_features_):
        v += _esperado_por_coalizao(arvore, X[:, atributos], mascaras[:, atributos], _valor_folhas(arvore))
    v /= len(modelo.estimators_)

    phi = np.zeros((n, m))
    tamanho = mascaras.sum(axis=1)
    for j in range(m):
        sem_j = ~mascaras[:, j]
        for c in np.flatnonzero(sem_j):
            s = tamanho[c]
            peso = factorial(s) * factorial(m - s - 1) / factorial(m)
            phi[:, j] += peso * (v[c | (1 << j)] - v[c])
    return -phi, float(v[0].mean())


METODO_BIBLIOTECA = "biblioteca shap (TreeExplainer)"
METODO_PROPRIO = "TreeSHAP exato (implementação própria)"


def calcular_shap(modelo: IsolationForest, X: np.ndarray) -> tuple[np.ndarray, str]:
    """
    Contribuições SHAP de cada atributo, com o sinal "positivo = mais atípico".
    Retorna (valores[n, m], método usado).
    """
    if shap is not None:
        try:
            valores = np.asarray(shap.TreeExplainer(modelo).shap_values(X), dtype=float)
            if valores.shape == X.shape:
                # Confere o sentido: no Isolation Forest, quanto maior o
                # score_samples, mais NORMAL é o contrato. Se a soma das
                # contribuições sobe junto com ele, inverte o sinal.
                soma = valores.sum(axis=1)
                if len(X) > 1 and np.std(soma) > 0:
                    if np.corrcoef(soma, modelo.score_samples(X))[0, 1] > 0:
                        valores = -valores
                return valores, METODO_BIBLIOTECA
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
    return f"{_num(fracao * 100, 1 if fracao < 0.01 else 0)}%"


def _descrever(atributo: str, linha: pd.Series) -> str:
    if atributo == "valor":
        return f"Valor {_num(linha['_razao'])}x a mediana da categoria"
    if atributo == "valor_habitante":
        return f"Valor por habitante {_num(linha['_razao'])}x a mediana da categoria"
    if atributo == "vigencia":
        return f"Vigência de {_num(linha['_duracao'], 0)} dias"
    if atributo == "concentracao":
        return (
            f"Fornecedor recebe {_pct(linha['_fatia'])} do valor do órgão, "
            f"{_num(linha['_vezes_media'], 0)}x a fatia média por fornecedor"
        )
    if atributo == "recorrencia":
        return f"Fornecedor com {_num(linha['_n_contratos'], 0)} contratos no órgão"
    return ATRIBUTOS_ROTULO.get(atributo, atributo)


def _motivo(linha: pd.Series, atributos: list[str]) -> str:
    # só atributos que estão de fato ACIMA do padrão (x > 0) e empurram para atípico
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
    df = df.copy()
    df["scoreRisco"] = 0.0
    df["scoreIF"] = np.nan
    df["risco"] = "Não avaliado"
    df["anomalia"] = False
    df["motivoRisco"] = ""
    df["grupoModelo"] = _grupo_modelo(df)
    df["alertaCadastro"] = alertas_cadastro(df)
    for atributo in ATRIBUTOS_ROTULO:
        df[f"shap_{atributo}"] = np.nan    # contribuição SHAP (só Alto e Médio)
        df[f"desvio_{atributo}"] = np.nan  # valor do atributo usado no modelo (desvio robusto, >= 0)

    if len(df) < MINIMO_CONTRATOS:
        return df, {"aplicado": False, "motivo": f"São necessários ao menos {MINIMO_CONTRATOS} contratos."}

    categoria_proc = df.get("categoriaProcesso.nome", pd.Series("", index=df.index)).fillna("")
    alienacao = categoria_proc.str.startswith(ALIENACAO)
    df.loc[alienacao, "motivoRisco"] = "Alienação: venda de bens pelo governo (receita, não despesa)"

    fatia_forn, vezes_media_forn, n_contratos_forn = _relacao_fornecedor(df)
    duracao = _duracao_dias(df)
    populacao = pd.to_numeric(df.get("populacao"), errors="coerce")

    grupos_info = {}
    metodos_shap: set[str] = set()
    for grupo, idx in df.index[~alienacao].groupby(df.loc[~alienacao, "grupoModelo"]).items():
        sub = df.loc[idx]
        if len(sub) < MINIMO_CONTRATOS:
            df.loc[idx, "motivoRisco"] = "Grupo com poucos contratos para comparação"
            grupos_info[grupo] = {"contratos": len(sub), "avaliado": False}
            continue

        municipal = grupo.startswith("Municipal")
        empenho = grupo.endswith("Empenho")
        categoria = sub["categoriaEspecificaEnum"]

        # --- valor (por habitante nos municipais) ---
        log_valor = np.log(sub["valor"].astype(float).clip(lower=1.0))
        pop = populacao.loc[idx]
        usa_habitante = municipal and pop.notna().mean() > 0.9
        if usa_habitante:
            log_valor = log_valor - np.log(pop.fillna(pop.median()).clip(lower=1.0))
        z_valor, mediana_valor = _z_robusto(log_valor, categoria)

        atributos = ["valor_habitante" if usa_habitante else "valor"]
        colunas = {atributos[0]: z_valor.clip(lower=0)}

        # --- vigência (só contratos) ---
        if not empenho:
            dur = duracao.loc[idx]
            log_dur = np.log1p(dur.clip(lower=0).fillna(dur.median() if dur.notna().any() else 0))
            z_dur, _ = _z_robusto(log_dur, categoria)
            atributos.append("vigencia")
            colunas["vigencia"] = z_dur.clip(lower=0)

        # --- relação com o fornecedor (comparada com o próprio grupo) ---
        mesmo_grupo = pd.Series(0, index=idx)
        z_conc, _ = _z_robusto(np.log(vezes_media_forn.loc[idx].clip(lower=1e-6)), mesmo_grupo)
        z_rec, _ = _z_robusto(np.log1p(n_contratos_forn.loc[idx]), mesmo_grupo)
        atributos += ["concentracao", "recorrencia"]
        colunas["concentracao"] = z_conc.clip(lower=0)
        colunas["recorrencia"] = z_rec.clip(lower=0)

        X = np.nan_to_num(pd.DataFrame(colunas)[atributos].to_numpy(dtype=float))
        for j, atributo in enumerate(atributos):
            df.loc[idx, f"desvio_{atributo}"] = X[:, j]

        modelo = IsolationForest(n_estimators=N_ARVORES, random_state=SEMENTE, n_jobs=-1)
        modelo.fit(X)
        score = pd.Series(-modelo.score_samples(X), index=idx)
        percentil = score.rank(pct=True, method="average")

        df.loc[idx, "scoreIF"] = score
        df.loc[idx, "scoreRisco"] = (percentil * 100).round(1)
        df.loc[idx, "risco"] = np.select(
            [percentil >= PERCENTIL_ALTO, percentil >= PERCENTIL_MEDIO], ["Alto", "Médio"], "Baixo"
        )

        # --- SHAP para os sinalizados (Alto e Médio) ---
        sinalizado = (percentil >= PERCENTIL_MEDIO).to_numpy()
        if sinalizado.any():
            valores_shap, metodo = calcular_shap(modelo, X[sinalizado])
            metodos_shap.add(metodo)
            idx_sinal = idx[sinalizado]
            for j, atributo in enumerate(atributos):
                df.loc[idx_sinal, f"shap_{atributo}"] = valores_shap[:, j]

            apoio = df.loc[idx_sinal, [f"shap_{a}" for a in atributos] + [f"desvio_{a}" for a in atributos]].copy()
            apoio["_razao"] = np.exp((log_valor - mediana_valor).loc[idx_sinal])
            apoio["_duracao"] = duracao.loc[idx_sinal].fillna(0)
            apoio["_fatia"] = fatia_forn.loc[idx_sinal]
            apoio["_vezes_media"] = vezes_media_forn.loc[idx_sinal]
            apoio["_n_contratos"] = n_contratos_forn.loc[idx_sinal]
            df.loc[idx_sinal, "motivoRisco"] = apoio.apply(_motivo, axis=1, atributos=atributos)

        grupos_info[grupo] = {
            "contratos": len(sub),
            "avaliado": True,
            "atributos": atributos,
        }

    df["anomalia"] = df["risco"] == "Alto"

    info = {
        "aplicado": True,
        "n_contratos": len(df),
        "avaliados": int((df["risco"] != "Não avaliado").sum()),
        "nao_avaliados": int((df["risco"] == "Não avaliado").sum()),
        "alto": int((df["risco"] == "Alto").sum()),
        "medio": int((df["risco"] == "Médio").sum()),
        "alertas_cadastro": int((df["alertaCadastro"] != "").sum()),
        "grupos": grupos_info,
        "metodo_shap": " + ".join(sorted(metodos_shap)) if metodos_shap else None,
    }
    return df, info