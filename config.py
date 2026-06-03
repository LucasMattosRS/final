import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_DIR  = os.path.join(BASE_DIR, "input_pdf")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_excel")
TEMP_DIR   = os.path.join(BASE_DIR, "temp")
DEBUG_DIR  = os.path.join(BASE_DIR, "debug")
LOG_DIR    = os.path.join(BASE_DIR, "logs")

# Escala de renderizacao do PDF para imagem
PDF_RENDER_SCALE = 3

# Raio de busca de texto ao redor do destino da seta (unidades PDF)
# Aumentado de 60 para 90 - captura tokens mais distantes da ponta da seta
ASSOCIATION_RADIUS = 90

# Distancia maxima de uma linha ao rotulo P/V (pixels na imagem escalada)
ARROW_MAX_DISTANCE = 80

# Pasta para imagens de auditoria
AUDITORIA_DIR = "auditoria"

# Arquivo de log de tokens nao reconhecidos (alimenta o dicionario)
TOKENS_NAO_RECONHECIDOS_LOG = os.path.join(LOG_DIR, "tokens_nao_reconhecidos.log")
