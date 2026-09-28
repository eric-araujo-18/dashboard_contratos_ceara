"""Caminhos do projeto (mesma convenção do mapa.py: BASE_DIR = raiz do projeto)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
CONTRATOS_DIR = DATA_DIR / "contratos"          # CSVs brutos baixados do PNCP
PROCESSADOS_DIR = DATA_DIR / "processados"      # resultado da análise
GEOJSON_PATH = DATA_DIR / "geo" / "ceara.geojson.json"
IBGE_DIR = DATA_DIR / "ibge_csv"
POPULACAO_JSON = IBGE_DIR / "populacao_ceara_ibge_2022.json"
POPULACAO_CSV = IBGE_DIR / "populacao_ceara_ibge_2022.csv"