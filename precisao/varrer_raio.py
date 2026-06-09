"""
precisao/varrer_raio.py
───────────────────────
ITEM 2 — Tunar a associação seta→texto COM dados, não no chute.

Roda o pipeline em um pequeno subconjunto de obras para vários valores de
ASSOCIATION_RADIUS e mostra, para cada raio:
   - taxa de preenchimento das colunas dedicadas
   - se houver gabarito preenchido: o % de acerto (o que realmente importa)

Assim você escolhe o raio que MAIS ACERTA, em vez do que mais preenche
(preencher errado é pior que não preencher).

⚠️ É lento: cada raio reprocessa as obras. Use poucas obras (2–3) já rotuladas.

Uso:
    python -m precisao.varrer_raio            # raios padrão, 2 obras
    python -m precisao.varrer_raio 60,90,120 3
"""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)

import main  # noqa: E402
from config import INPUT_DIR  # noqa: E402

VAL_COLS = ["logradouro", "ancoragem", "lado_forte",
            "metragem", "material", "altura_poste"]


def _carregar_gabarito():
    import csv
    import unicodedata
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gabarito.csv")
    if not os.path.exists(p):
        return None

    def norm(s):
        s = str(s or "").strip().upper()
        s = "".join(c for c in unicodedata.normalize("NFD", s)
                    if unicodedata.category(c) != "Mn")
        return " ".join(s.split())

    with open(p, encoding="utf-8") as f:
        gab = {}
        for l in csv.DictReader(f):
            chave = (norm(l.get("obra")), norm(l.get("folha")), norm(l.get("codigo")))
            gab[chave] = l
    return gab, norm


def main_sweep():
    raios = [60, 90, 120]
    n_obras = 2
    if len(sys.argv) > 1:
        raios = [int(x) for x in sys.argv[1].split(",")]
    if len(sys.argv) > 2:
        n_obras = int(sys.argv[2])

    grupos = list(main.group_pdfs_by_obra(INPUT_DIR).items())[:n_obras]
    gab = _carregar_gabarito()

    print(f"\nVarrendo raios {raios} em {n_obras} obra(s)...\n")
    print(f"  {'raio':>5} | {'preench.':>9} | {'acerto':>7}")
    print(f"  {'-'*5}-+-{'-'*9}-+-{'-'*7}")

    for r in raios:
        main.ASSOCIATION_RADIUS = r  # injeta o raio nesta execução
        linhas = []
        for _, pdfs in grupos:
            for pdf in pdfs:
                try:
                    linhas.extend(main.process_pdf(pdf))
                except Exception:  # noqa: BLE001
                    pass
        if not linhas:
            continue
        preench = sum(1 for ln in linhas for c in VAL_COLS
                      if str(ln.get(c, "")).strip())
        tot_cells = len(linhas) * len(VAL_COLS)
        pct_pre = 100 * preench / max(tot_cells, 1)

        acerto = "—"
        if gab:
            gabdict, norm = gab
            certo = total = 0
            for ln in linhas:
                chave = (norm(ln.get("obra")), norm(ln.get("folha")), norm(ln.get("codigo")))
                g = gabdict.get(chave)
                if not g:
                    continue
                for c in VAL_COLS:
                    if str(g.get(c, "")).strip():
                        total += 1
                        if norm(ln.get(c, "")) == norm(g.get(c)):
                            certo += 1
            if total:
                acerto = f"{100*certo/total:5.1f}%"

        print(f"  {r:>5} | {pct_pre:>8.1f}% | {acerto:>7}")

    print("\n  Escolha o raio com MAIOR acerto (não o de maior preenchimento).\n")


if __name__ == "__main__":
    main_sweep()
