import os
import re
import logging

logger = logging.getLogger(__name__)

# Padrão esperado: <codigo_obra>_<descricao>_<folha>.pdf
# Ex: 17176206_Desenho 1_1.pdf → obra=17176206, folha=1
_NAME_RE = re.compile(r'^(\d+)_(.+?)_(\d+)\.pdf$', re.IGNORECASE)


def get_work_number(pdf_path: str) -> str:
    """Extrai o código da obra do nome do arquivo."""
    file_name = os.path.basename(pdf_path)
    match = _NAME_RE.match(file_name)
    if match:
        return match.group(1)
    # Fallback: usa tudo antes do primeiro underscore, mas avisa
    fallback = file_name.split("_")[0]
    logger.warning(
        "Nome de arquivo fora do padrão esperado '<obra>_<desc>_<folha>.pdf': %s "
        "→ usando '%s' como código de obra.",
        file_name, fallback,
    )
    return fallback


def get_sheet_number(pdf_path: str) -> int:
    """Extrai o número da folha/sequência do nome do arquivo."""
    file_name = os.path.basename(pdf_path)
    match = _NAME_RE.match(file_name)
    if match:
        return int(match.group(3))
    return 1
