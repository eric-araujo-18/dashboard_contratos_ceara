"""
Classificação dos contratos em 22 categorias específicas.

Convertido do notebook notebooks/classificador.ipynb para um módulo .py
normal (mesmo motivo dos demais).

1) Regras por palavra-chave (utils/regras_classificacao.py).
2) Modelo de ML (TF-IDF + regressão logística via SGD) treinado com os
   contratos que as regras conseguiram classificar, usado para
   reclassificar os "Outros" quando o modelo está confiante.

O resultado fica numa única coluna, "categoria", com o nome da categoria.
Os números (1 a 22) só existem aqui dentro, para as regras e o modelo.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import train_test_split

from utils.regras_classificacao import (
    ORDEM_COMPRAS,
    ORDEM_SERVICOS,
    REGRAS_COMPRAS,
    REGRAS_SERVICOS,
    normalizar_texto,
)

ENUM_OUTROS = 22

# Nome de cada categoria: é o que fica na coluna "categoria" e aparece no painel
NOMES_CURTOS = {
    1: "Alimentos", 2: "Combustíveis", 3: "Equipamentos",
    4: "Material de expediente", 5: "Material de limpeza", 6: "Médico-hospitalar",
    7: "Medicamentos", 8: "Mobiliário", 9: "Peças e acessórios",
    10: "Obras e engenharia", 11: "Serviços administrativos", 12: "Consultoria",
    13: "Educação e capacitação", 14: "Limpeza e conservação", 15: "Locação",
    16: "Manutenção", 17: "Serviços de saúde", 18: "Tecnologia da informação",
    19: "Transporte escolar", 20: "Publicidade e eventos", 21: "Alienação de bens",
    22: "Outros",
}
_ENUM_POR_NOME = {nome: enum for enum, nome in NOMES_CURTOS.items()}
NOME_OUTROS = NOMES_CURTOS[ENUM_OUTROS]

# Palavras que não dizem nada sobre o objeto ("CONTRATO 03", "CONTRATO CULTURA")
_PALAVRAS_VAZIAS = {
    "de", "da", "do", "das", "dos", "e", "a", "o", "as", "os", "para", "com", "em", "no", "na",
    "nos", "nas", "ao", "aos", "contrato", "contratos", "termo", "aditivo", "ref",
}
MINIMO_PALAVRAS = 2


def _descricao_informativa(texto: str) -> bool:
    """
    O objeto tem pelo menos MINIMO_PALAVRAS palavras que dizem algo sobre o que
    foi contratado? Sem isso, o modelo de texto "chuta" com confiança alta a
    categoria mais comum: nos testes, as 69 descrições com uma palavra ou
    nenhuma ("CONTRATO CULTURA", "CONTRATO INFRA") foram todas para Obras e
    engenharia. Essas ficam em "Outros".
    """
    palavras = [p for p in texto.split() if p not in _PALAVRAS_VAZIAS and not p.isdigit() and len(p) > 1]
    return len(palavras) >= MINIMO_PALAVRAS

# categoriaProcesso.id (PNCP) que já determina a categoria específica
_CATEGORIA_DIRETA = {1: 15, 3: 18, 5: 15, 6: 11, 7: 10, 9: 10, 10: 17, 11: 21}
_ID_COMPRAS, _ID_SERVICOS = 2, 8

_REGRAS_GERAIS = {**REGRAS_COMPRAS, **REGRAS_SERVICOS}
_ORDEM_GERAL = ORDEM_COMPRAS + ORDEM_SERVICOS


def _compilar(regras: dict) -> dict:
    return {enum: re.compile(padrao) for enum, padrao in regras.items()}


_C_COMPRAS = _compilar(REGRAS_COMPRAS)
_C_SERVICOS = _compilar(REGRAS_SERVICOS)
_C_GERAIS = _compilar(_REGRAS_GERAIS)


def _por_regras(texto: str, compiladas: dict, ordem: list) -> int:
    for enum in ordem:
        padrao = compiladas.get(enum)
        if padrao is not None and padrao.search(texto):
            return enum
    return ENUM_OUTROS


def classificar_por_regras(df: pd.DataFrame) -> pd.DataFrame:
    """
    Contratos sem categoriaProcesso.id (ou com id fora da lista) são
    classificados pelas regras gerais em vez de serem descartados.
    """
    df = df.copy()
    # texto normalizado só para as regras; não fica no DataFrame (repetiria "objeto")
    textos = df["objeto"].map(normalizar_texto)

    if "categoriaProcesso.id" in df.columns:
        ids = pd.to_numeric(df["categoriaProcesso.id"], errors="coerce")
    else:
        ids = pd.Series(np.nan, index=df.index)

    enums = []
    for texto, cid in zip(textos, ids):
        if cid in _CATEGORIA_DIRETA:
            enum = _CATEGORIA_DIRETA[int(cid)]
        elif cid == _ID_COMPRAS:
            enum = _por_regras(texto, _C_COMPRAS, ORDEM_COMPRAS)
            if enum == ENUM_OUTROS:
                enum = _por_regras(texto, _C_SERVICOS, ORDEM_SERVICOS)
        elif cid == _ID_SERVICOS:
            enum = _por_regras(texto, _C_SERVICOS, ORDEM_SERVICOS)
        else:
            enum = _por_regras(texto, _C_GERAIS, _ORDEM_GERAL)
        enums.append(enum)

    df["categoria"] = [NOMES_CURTOS[e] for e in enums]
    return df


def refinar_outros_com_ml(
    df: pd.DataFrame,
    limiar: float = 0.60,
    minimo_treino: int = 300,
) -> tuple[pd.DataFrame, dict]:
    """
    Treina um classificador de texto com os contratos já classificados
    pelas regras e reclassifica os "Outros" quando a confiança do
    modelo é >= limiar. Só entram os "Outros" com descrição informativa
    (_descricao_informativa). Base pequena demais → não faz nada (info
    explica o motivo).
    """
    df = df.copy()
    textos = df["objeto"].map(normalizar_texto)
    # o modelo treina com o número de cada categoria (1 a 22); na base fica o nome
    enums = df["categoria"].map(_ENUM_POR_NOME)
    info = {"aplicado": False, "outros_antes": int((enums == ENUM_OUTROS).sum())}

    rotulados = enums != ENUM_OUTROS
    outros = ~rotulados

    contagem = enums[rotulados].value_counts()
    classes_ok = contagem[contagem >= 5].index
    treino = rotulados & enums.isin(classes_ok)

    if treino.sum() < minimo_treino or len(classes_ok) < 2:
        info["motivo"] = "Poucos contratos classificados para treinar o modelo."
        return df, info
    if outros.sum() == 0:
        info["motivo"] = "Nenhum contrato em 'Outros'."
        return df, info

    x, y = textos[treino], enums[treino]
    x_tr, x_te, y_tr, y_te = train_test_split(
        x, y, test_size=0.2, random_state=42,
        stratify=y if y.value_counts().min() >= 2 else None,
    )

    def novo_modelo():
        vetor = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=30000)
        clf = SGDClassifier(loss="log_loss", alpha=1e-5, max_iter=30, tol=1e-3, random_state=42)
        return vetor, clf

    # 1) avaliação em holdout
    vetor, clf = novo_modelo()
    clf.fit(vetor.fit_transform(x_tr), y_tr)
    info["acuracia_holdout"] = float(clf.score(vetor.transform(x_te), y_te))

    # 2) modelo final com todos os rotulados
    vetor, clf = novo_modelo()
    clf.fit(vetor.fit_transform(x), y)

    # só os "Outros" cuja descrição diz o que foi contratado
    candidatos = outros & textos.map(_descricao_informativa)
    reclassificados = 0
    if candidatos.any():
        proba = clf.predict_proba(vetor.transform(textos[candidatos]))
        confianca = proba.max(axis=1)
        previsto = clf.classes_[proba.argmax(axis=1)]

        aceitos = confianca >= limiar
        indices = df.index[candidatos][aceitos]
        df.loc[indices, "categoria"] = [NOMES_CURTOS[int(e)] for e in previsto[aceitos]]
        reclassificados = int(aceitos.sum())

    info.update(
        aplicado=True,
        limiar=limiar,
        n_treino=int(treino.sum()),
        sem_descricao=int((outros & ~candidatos).sum()),
        reclassificados=reclassificados,
        outros_depois=int((df["categoria"] == NOME_OUTROS).sum()),
    )
    return df, info