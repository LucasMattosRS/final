import re
import json
import os
from rapidfuzz import process

# ── Dicionario ────────────────────────────────────────────────────────────────

DICIONARIO_BASE = [
    "C09x300", "C09x600", "C10x300", "C10x600", "C11x600",
    "C12x300", "C12x600", "C12x1000", "C14x600", "C14x1000",
    "M10x300", "M10x600", "M11x300", "M12x300",
    "SMFL", "SMPI", "SMDT", "SMAN", "SMTG", "SMTR",
    "CE1", "CE2", "CE3", "CE4", "CE-SH", "CEAFC1", "CEAFC4", "CEAFS",
    "S43(1)", "S43(3)", "S44(1)", "S44(2)", "S44(3)", "S44(4)",
    "S45(1)", "S45(3)", "S47(2)", "S144-1", "S144-2", "S145", "S150-0",
    "B1F", "B1M", "B2F", "B2M", "B4A", "B4F", "B4M",
    "BF-A", "CF-H", "M1F", "M1M", "M3F",
    "PRE1", "PRE3", "PRE4", "ET4A", "ET1A",
    "IP", "1AF(1)", "L1(1)", "L1(2)", "L2",
    "1x3x120(70)AX", "1x3x240(120)AX", "1x3x70(70)AX",
    "2x1/0AN(4AN)", "4x1/0AN",
    "3x185AX(5AZN)", "3x70AX(5AZN)", "3x300AX-Q(6AZN)", "3x336AN",
    "25KVA", "37,5KVA", "45KVA", "75KVA", "112,5KVA",
    "15KV_1T(ABC)", "15KV_1F1(A)", "15KV_1L(C)", "15KV_PDRT(ABC)",
    "BT", "MT", "BT0", "CORDOALHA", "RAMAL", "RAMAIS", "BIF", "TRIF",
    "BCU", "GD", "NF", "TRAFO", "BLINDAR", "REAPROVEITAR",
]

_CORRECOES_FIXAS = {
    "C0GX600":  "C09X600",
    "C0GX1000": "C09X1000",
    "SMFI":     "SMFL",
    "SMFIL":    "SMFL",
    "DTI1":     "DT11",
    "S442":     "S44(2)",
    "S462":     "S46(2)",
    "Ll(2)":    "L1(2)",
    "LI(2)":    "L1(2)",
}

_FUZZY_THRESHOLD = 82


def _carregar_dicionario() -> list:
    json_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "dicionario.json")
    )
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, list):
                return dados
            if isinstance(dados, dict):
                return dados.get("dicionario", DICIONARIO_BASE)
        except Exception:
            pass
    return DICIONARIO_BASE


DICIONARIO = _carregar_dicionario()


# ── Problema 2 corrigido ──────────────────────────────────────────────────────
# Tokens colados como "C12X600112,5KVAB4A" precisam ser segmentados antes
# do fuzzy match. A estrategia: tenta separar por padroes conhecidos
# (letra maiuscula seguida de digitos, virgula decimal, etc.) antes de
# aplicar o fuzzy token a token.

# Separadores naturais presentes nos tokens colados
_SEP_RE = re.compile(
    r'(?<=[A-Z0-9)])(?=[A-Z]{2,}(?:\d|\())'  # fim de token / inicio de outro
    r'|(?<=\d)(?=[A-Z]{2})'                   # digito seguido de 2+ letras
    r'|(?<=\d),(?=\d)'                         # virgula decimal — preserva
    r'|(?<=\))(?=[A-Z0-9])',                   # fecha parenteses / novo token
)

# Tokens que sao numeros puros ou metragens — nao entram no fuzzy
_NUMERO_RE = re.compile(r'^\d+([.,]\d+)?\s*[mM]?$')


# Classes de transformador válidas (lista branca) — evita partir 112,5KVA em 1 + 12,5KVA
_KVA_CLASSE = r'(?:112,5|37,5|150|300|25|45|75|15)\s*KVA'


def _segmentar_token(token: str) -> list[str]:
    """
    Tenta separar um token colado em sub-tokens.
    Ex: "C12X600112,5KVAB4A" -> ["C12X600", "112,5KVA", "B4A"]
    Usa lista branca das classes KVA para não fatiar o valor (112,5 -> 1 + 12,5).
    """
    partes = re.split(
        r'(?=[CM]\d{2}[xX])'         # inicio de poste     C12x / M10x
        r'|(?<=KVA)'                  # logo apos uma classe KVA -> novo token
        r'|(?=' + _KVA_CLASSE + r')'  # antes de uma classe KVA
        r'|(?=S\d{2}\()'             # classificacao       S44(
        r'|(?=SM[A-Z]{2})'           # conjunto            SMFL / SMPI
        r'|(?=CE[\dA\-])'             # classe eng          CE4 / CE-SH
        r'|(?=ET\d)'                  # equipamento         ET4A
        r'|(?=PRE\d)'                 # protecao            PRE4
        r'|(?=BF-|CF-)'               # ferragem            BF-A / CF-H
        r'|(?=B\dF)|(?=M\dF)|(?=M\dM)|(?=M\dA)'  # bracos/montagens
        r'|(?=L\d\()',                # lampada             L1(
        token,
        flags=re.IGNORECASE,
    )
    return [p.strip() for p in partes if p.strip()]


def corrigir_token(token: str) -> str:
    if _NUMERO_RE.match(token):
        return token
    resultado = process.extractOne(token, DICIONARIO)
    if resultado:
        texto, score, _ = resultado
        if score >= _FUZZY_THRESHOLD:
            return texto
    return token


def corrigir_texto(texto: str) -> dict:
    """
    1. Aplica correcoes fixas.
    2. Segmenta tokens colados.
    3. Aplica fuzzy em cada sub-token.
    """
    original = texto
    upper = texto.upper()

    # Correcoes fixas
    for erro, correto in _CORRECOES_FIXAS.items():
        upper = upper.replace(erro.upper(), correto)

    # Quebra em partes por separadores naturais (virgula, espaco)
    partes_brutas = re.split(r'([,\s]+)', upper)

    tokens_saida = []
    houve = False

    for parte in partes_brutas:
        p = parte.strip()
        if not p:
            tokens_saida.append(parte)
            continue

        # Tenta segmentar tokens colados
        sub_tokens = _segmentar_token(p)

        if len(sub_tokens) > 1:
            # Era um token colado — corrige cada parte (junta com espaço para
            # não confundir com a vírgula decimal de 112,5KVA)
            corrigidos = [corrigir_token(s) for s in sub_tokens]
            tokens_saida.append(" ".join(corrigidos))
            houve = True
        else:
            corrigido = corrigir_token(p)
            if corrigido != p:
                houve = True
            tokens_saida.append(corrigido)

    resultado_final = "".join(tokens_saida)
    houve = houve or (resultado_final != original.upper())

    return {
        "original":       original,
        "corrigido":      resultado_final,
        "houve_correcao": houve,
    }
