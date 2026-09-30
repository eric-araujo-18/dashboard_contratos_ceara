# Dashboard de Contratos Públicos do Ceará

Plataforma para visualização e detecção de comportamentos atípicos
em contratos públicos dos municípios do Ceará.

## Tecnologias

- Python, Pandas, NumPy
- Streamlit
- Scikit-learn (Isolation Forest, TF-IDF + regressão logística)
- SHAP (TreeSHAP exato, implementado no projeto)
- D3.js + GeoJSON
- Dados: PNCP e IBGE (Censo 2022)

## Estrutura

```
.streamlit/config.toml   tema (precisa ficar na raiz para o Streamlit Cloud)
requirements.txt
streamlit/
  app/app.py             interface
  app/utils/             pipeline: PNCP, tratamento, classificação, IBGE, anomalias, mapa
  app/components/        mapa em D3.js (componente com clique para filtrar)
  data/                  contratos, GeoJSON e população
site/                    página de apresentação (Next.js)
```

## Executando

Na raiz do projeto:

```bash
py -m venv venv
venv\Scripts\activate          # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
streamlit run streamlit/app/app.py
```

Rodar a partir da raiz garante que o tema de `.streamlit/config.toml` seja
aplicado, igual ao Streamlit Cloud.

## Modelo de detecção de anomalias

- **Um Isolation Forest por grupo comparável**: esfera do órgão (municipal,
  estadual, federal) x tipo de documento (contrato ou empenho). Cada contrato
  só é comparado com contratos parecidos.
- **Fora do modelo** ("Não avaliado"): alienações (venda de bens pelo governo,
  que é receita) e grupos com menos de 50 contratos.
- **Atributos** (desvio robusto por mediana/MAD, só o lado "acima do padrão"):
  valor em relação à categoria (por habitante nos municipais), vigência em
  relação à categoria (só contratos), concentração do valor do órgão no mesmo
  fornecedor e número de contratos do fornecedor com o órgão.
- **Nível de risco**: percentil dentro do grupo. Alto = 5% mais atípicos,
  Médio = faixa seguinte de 10%. É um ranking de prioridade, não uma contagem
  de irregularidades.
- **Explicação**: valores SHAP exatos (TreeSHAP "tree path dependent") da
  profundidade média do Isolation Forest, calculados para os contratos Alto e
  Médio.
- **Erros de cadastro** (valor simbólico, datas inconsistentes, assinatura
  depois da publicação) aparecem num alerta separado, fora do risco.

Atipicidade estatística não significa irregularidade: o dashboard indica
onde vale olhar primeiro.