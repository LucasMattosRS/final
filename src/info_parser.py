import re

# ── Metragem (para VAO) ───────────────────────────────────────────────────────
_METRAGEM_TOKEN_RE = re.compile(
    r'^\d{1,4}[.,]?\d{0,3}\s*[mM]$'
)
_METRAGEM_VALOR_RE = re.compile(
    r'(\d{1,4}[.,]\d{1,3}|\d{1,4})\s*[mM]'
)


def parse_metragem(textos: list[str]) -> str:
    """
    Extrai a primeira metragem em metros da lista de textos próximos.
    """
    # Passagem 1: token único com unidade
    for texto in textos:
        t = str(texto).strip()
        if _METRAGEM_TOKEN_RE.match(t):
            return t.lower().replace(" ", "")

    # Passagem 2: número puro seguido de 'm' no próximo token
    for i, texto in enumerate(textos):
        t = str(texto).strip()
        if re.match(r'^\d{1,4}[.,]?\d{0,3}$', t) and i + 1 < len(textos):
            prox = str(textos[i + 1]).strip().lower()
            if prox == "m":
                return f"{t}m"

    # Passagem 3: regex dentro de string composta
    for texto in textos:
        m = _METRAGEM_VALOR_RE.search(str(texto))
        if m:
            return m.group().strip().lower().replace(" ", "")

    return ""


# ── Material do poste (para POSTE) ───────────────────────────────────────────
# Formato padrão: C12x600, C12x1000, M10x300 etc.
_EQUIP_RE = re.compile(r'([CM])(\d{2})x(\d+)', re.IGNORECASE)

# Token isolado C ou M
_TOKEN_CM_RE = re.compile(r'^([CM])$', re.IGNORECASE)

# Classificação S44(2), S46(2) etc. — indica especificação de carga do poste
_CLASSIF_RE = re.compile(r'S(\d{2})\((\d)\)', re.IGNORECASE)

_LABEL = {"C": "CONCRETO", "M": "MADEIRA"}


def parse_material(textos: list[str]) -> str:
    """
    Extrai o material do poste da lista de textos próximos.
    Prioriza o código completo (C12x600 → CONCRETO) sobre tokens isolados.
    Também reconhece blocos concatenados como 'C12x600,CE4,SMFL,IP'.
    """
    fallback = ""

    for texto in textos:
        t = str(texto).strip()

        # Procura código completo dentro do texto (mesmo embutido em string maior)
        m = _EQUIP_RE.search(t)
        if m:
            return _LABEL[m.group(1).upper()]

        # Token isolado C ou M como fallback
        if not fallback and _TOKEN_CM_RE.match(t):
            fallback = _LABEL[t.upper()]

    return fallback


def parse_altura_poste(textos: list[str]) -> str:
    """
    Extrai a altura do poste em metros.
    Ex: C09x600 → '9m', C12x1000 → '12m', M10x300 → '10m'
    """
    for texto in textos:
        m = _EQUIP_RE.search(str(texto).strip())
        if m:
            return f"{int(m.group(2))}m"
    return ""


def parse_classificacao(textos: list[str]) -> str:
    """
    Extrai a classificação de carga do poste.
    Ex: S44(2) → '44/2', S46(2) → '46/2'
    """
    for texto in textos:
        m = _CLASSIF_RE.search(str(texto).strip())
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    return ""


def parse_equipamentos(textos: list[str]) -> list[str]:
    """
    Extrai lista de equipamentos associados ao poste.
    Ex: 'C12x600,CE4,SMFL,IP' → ['C12x600', 'CE4', 'SMFL', 'IP']
    Útil para auditoria e exportação detalhada.
    """
    equips = []
    _EQUIP_LIST_RE = re.compile(
        r'(C\d{2}x\d+|M\d{2}x\d+|SMFL|SMPI|SMDT|SMAN|SMTR|'
        r'CE\d|CE-\w+|BF-\w|IP|L\d\(\d\)|DT\d{2}|S\d{2}\(\d\)|'
        r'DCIM|SMAN|CORDOALHA)',
        re.IGNORECASE
    )
    for texto in textos:
        for match in _EQUIP_LIST_RE.finditer(str(texto)):
            val = match.group().upper()
            if val not in equips:
                equips.append(val)
    return equips

import re

_LOGRADOURO_RE = re.compile(
    r"\b(AV\.?|AVENIDA|RUA|ROD\.?|RODOVIA|ESTRADA|ALAMEDA|TRAVESSA)\s+[A-Z0-9ÁÀÂÃÉÊÍÓÔÕÚÇ\- ]{3,30}",
    re.IGNORECASE,
)

def parse_logradouro(textos):

    for texto in textos:

        texto = str(texto).strip()

        m = _LOGRADOURO_RE.search(texto)

        if m:
            return m.group(0).upper().strip()

    return ""

_ANCOR_RE   = re.compile(r"ANCOR", re.IGNORECASE)          # ANCORAR/ANCORAGEM/ANCORADO
_COD_NUM_RE = re.compile(r"\b(\d{5,})\b")                  # código tipo 4008661
# "LADO FORTE", "LADO-FORTE", com direção opcional logo a seguir (NORTE, SUL, ...)
_LADO_FORTE_RE = re.compile(
    r"LADO[\s\-]*FORTE(?:\s+([A-ZÀ-Ÿ]+))?",
    re.IGNORECASE,
)


def parse_ancoragem(textos: list[str]) -> str:
    """
    Retorna um flag limpo de ancoragem:
      - 'SIM (4008661)' quando há código logo após ANCORAR
      - 'SIM'           quando há ancoragem mas sem código
      - ''              quando não há menção
    """
    for texto in textos:
        s = str(texto)
        m = _ANCOR_RE.search(s)
        if m:
            depois = s[m.end():]
            cod = _COD_NUM_RE.search(depois)
            return f"SIM ({cod.group(1)})" if cod else "SIM"
    return ""


def parse_lado_forte(textos: list[str]) -> str:
    """
    Extrai o LADO FORTE quando ele está escrito na planta.
    Junta 'LADO' + 'FORTE' mesmo que tenham sido separados no agrupamento.
    Retorna a direção (ex.: 'NORTE') quando informada, senão 'SIM'.
    Obs.: muitas plantas não trazem este dado escrito — nesse caso fica vazio.
    """
    for texto in textos:
        s = str(texto)
        m = _LADO_FORTE_RE.search(s)
        if m:
            direcao = (m.group(1) or "").strip().upper()
            return direcao if direcao else "SIM"
    return ""