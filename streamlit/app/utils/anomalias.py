"""
Detecção de contratos atípicos com Isolation Forest.

Convertido do notebook notebooks/anomalias.ipynb para um módulo .py
normal (mesmo motivo dos demais).

Features por contrato:
  - valor (log)
  - desvio robusto do valor em relação à mediana da própria categoria
  - valor por habitante do município (IBGE)
  - duração da vigência
  - concentração: fatia do valor do município que está com o mesmo fornecedor
  - quantidade de contratos do fornecedor no município

O resultado é um índice de risco (0-100 = posição no ranking de anomalia),
o nível (Baixo/Médio/Alto) e um texto com os motivos mais evidentes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

MINIMO_CONTRATOS = 50
MINIMO_CONTRATOS_MUNICIPIO = 5
MINIMO_CONTRATOS_CATEGORIA = 5
PERCENTIL_ALTO = 0.95
PERCENTIL_MEDIO = 0.85

# texto usado quando nenhuma regra explícita explica o contrato: aponta a
# feature que mais se afastou da média (mesma ordem das colunas de X)
DESTAQUES = [
    ("Valor absoluto muito alto", "Valor absoluto muito baixo"),
    ("Valor acima do padrão da categoria", "Valor abaixo do padrão da categoria"),
    ("Valor por habitante alto para o município", "Valor por habitante baixo para o município"),
    ("Vigência longa", "Vigência muito curta"),
    ("Fornecedor concentrado no município", "Fornecedor pouco concentrado no município"),
    ("Fornecedor com muitos contratos no município", "Fornecedor com poucos contratos no município"),
]


def _motivos(linha: pd.Series) -> str:
    m = []
    if linha["z_categoria"] > 3:
        m.append(f"Valor {linha['razao_mediana']:.1f}x a mediana da categoria")
    if linha["z_per_capita"] > 2.5:
        m.append("Valor por habitante muito alto para o município")
    if linha["share_fornecedor"] > 0.6:
        m.append(f"Fornecedor concentra {linha['share_fornecedor']:.0%} do valor do município")
    if linha["duracao_dias"] < 0:
        m.append("Datas de vigência inconsistentes")
    elif linha["duracao_dias"] > 1825:
        m.append("Vigência superior a 5 anos")
    if linha["assinatura_apos_publicacao"]:
        m.append("Assinatura posterior à publicação no PNCP")
    return "; ".join(m) if m else f"Combinação atípica (destaque: {linha['destaque']})"


def detectar_anomalias(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    df["scoreRisco"] = 0.0
    df["risco"] = "Baixo"
    df["anomalia"] = False
    df["motivoRisco"] = ""

    if len(df) < MINIMO_CONTRATOS:
        return df, {"aplicado": False, "motivo": f"São necessários ao menos {MINIMO_CONTRATOS} contratos."}

    valor = df["valor"].astype(float)
    log_valor = np.log1p(valor)

    # --- valor vs. categoria (desvio robusto: mediana e MAD) ---
    cat = df["categoriaEspecificaEnum"]
    mediana = log_valor.groupby(cat).transform("median")
    mad = (log_valor - mediana).abs().groupby(cat).transform("median") * 1.4826
    escala = mad.where(mad > 0, log_valor.std() or 1.0)
    n_cat = log_valor.groupby(cat).transform("size")
    z_categoria = ((log_valor - mediana) / escala).where(n_cat >= MINIMO_CONTRATOS_CATEGORIA, 0.0)
    razao_mediana = valor / np.expm1(mediana).clip(lower=1.0)

    # --- valor por habitante ---
    pop = pd.to_numeric(df.get("populacao"), errors="coerce")
    pop_mediana = pop.median()
    pop = pop.fillna(pop_mediana if pd.notna(pop_mediana) else 10_000).clip(lower=1)
    log_pc = np.log(valor / pop)
    z_pc = (log_pc - log_pc.mean()) / (log_pc.std() or 1.0)

    # --- vigência ---
    if {"dataVigenciaInicio", "dataVigenciaFim"} <= set(df.columns):
        duracao = (df["dataVigenciaFim"] - df["dataVigenciaInicio"]).dt.days
    else:
        duracao = pd.Series(np.nan, index=df.index)
    duracao_util = duracao.fillna(duracao.median() if duracao.notna().any() else 0)
    duracao_log = np.log1p(duracao_util.clip(lower=0))

    # --- concentração de fornecedor no município ---
    mun = df["municipioNorm"]
    forn = df["niFornecedor"].fillna("").astype(str) if "niFornecedor" in df.columns else pd.Series("", index=df.index)
    total_mun = valor.groupby(mun).transform("sum")
    n_mun = valor.groupby(mun).transform("size")
    total_forn = valor.groupby([mun, forn]).transform("sum")
    n_forn = valor.groupby([mun, forn]).transform("size")
    identificado = forn != ""
    share = (total_forn / total_mun).where((n_mun >= MINIMO_CONTRATOS_MUNICIPIO) & identificado, 0.0)
    n_forn_log = np.log1p(n_forn.where(identificado, 1))

    X = np.column_stack([log_valor, z_categoria, log_pc, duracao_log, share, n_forn_log])
    X = StandardScaler().fit_transform(np.nan_to_num(X))

    modelo = IsolationForest(n_estimators=200, random_state=42, n_jobs=-1)
    modelo.fit(X)
    anomalia = pd.Series(-modelo.score_samples(X), index=df.index)
    percentil = anomalia.rank(pct=True, method="average")

    df["scoreRisco"] = (percentil * 100).round(1)
    df["scoreIF"] = anomalia  # score bruto, para desempatar o ranking
    df["risco"] = np.select(
        [percentil >= PERCENTIL_ALTO, percentil >= PERCENTIL_MEDIO], ["Alto", "Médio"], "Baixo"
    )
    df["anomalia"] = df["risco"] == "Alto"

    coluna_destaque = np.abs(X).argmax(axis=1)
    sinal_destaque = X[np.arange(len(X)), coluna_destaque] >= 0
    destaque = [
        DESTAQUES[c][0 if positivo else 1]
        for c, positivo in zip(coluna_destaque, sinal_destaque)
    ]
    apos_publicacao = (
        df["assinaturaAposPublicacao"].fillna(False).astype(bool)
        if "assinaturaAposPublicacao" in df.columns
        else pd.Series(False, index=df.index)
    )
    # inconsistência de datas é um sinal de risco por si só: sobe para Médio
    df.loc[apos_publicacao & (df["risco"] == "Baixo"), "risco"] = "Médio"
    sinalizados = df["risco"] != "Baixo"

    apoio = pd.DataFrame(
        {
            "z_categoria": z_categoria,
            "razao_mediana": razao_mediana,
            "z_per_capita": z_pc,
            "share_fornecedor": share,
            "duracao_dias": duracao,
            "assinatura_apos_publicacao": apos_publicacao,
            "destaque": destaque,
        },
        index=df.index,
    )[sinalizados].fillna({"duracao_dias": 0})
    df.loc[sinalizados, "motivoRisco"] = apoio.apply(_motivos, axis=1)

    info = {
        "aplicado": True,
        "n_contratos": len(df),
        "alto": int((df["risco"] == "Alto").sum()),
        "medio": int((df["risco"] == "Médio").sum()),
    }
    return df, info