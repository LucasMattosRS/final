"""
precisao/medir.py
─────────────────
Compara precisao/saida_atual.csv (o que o sistema extraiu) com
precisao/gabarito.csv (o que você preencheu à mão) e imprime o % de acerto
por coluna. Casa as linhas por (obra, folha, codigo).

Regra de comparação: normaliza maiúsculas/minúsculas, espaços e acentos antes
de comparar, para não punir diferença cosmética. Células do gabarito em branco
são IGNORADAS (você não conferiu aquela).

Uso:
    1) python -m precisao.rodar         (gera saida_atual.csv)
    2) python -m precisao.gabarito      (gera o modelo)
    3) preencha gabarito.csv à mão
    4) python -m precisao.medir
"""
import os
import csv
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "saida_atual.csv")
GAB = os.path.join(AQUI, "gabarito.csv")

VAL_COLS = ["logradouro", "ancoragem", "lado_forte",
            "metragem", "material", "altura_poste"]


def _norm(s: str) -> str:
    s = str(s or "").strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return " ".join(s.split())


def _chave(linha):
    return (_norm(linha.get("obra")), _norm(linha.get("folha")),
            _norm(linha.get("codigo")))


def main():
    if not (os.path.exists(SAIDA) and os.path.exists(GAB)):
        print("Faltam arquivos. Rode rodar.py e gabarito.py, e preencha o gabarito.")
        return

    with open(SAIDA, encoding="utf-8") as f:
        saida = {_chave(l): l for l in csv.DictReader(f)}
    with open(GAB, encoding="utf-8") as f:
        gab = list(csv.DictReader(f))

    print(f"\n{'='*56}\n  ACERTO POR COLUNA\n{'='*56}")
    resumo = {}
    for c in VAL_COLS:
        certo = total = 0
        erros = []
        for g in gab:
            esperado = g.get(c, "")
            if not str(esperado).strip():
                continue  # célula não conferida → ignora
            total += 1
            obtido = saida.get(_chave(g), {}).get(c, "")
            if _norm(obtido) == _norm(esperado):
                certo += 1
            elif len(erros) < 3:
                erros.append((g.get("codigo"), esperado, obtido))
        resumo[c] = (certo, total)
        if total:
            print(f"\n  {c:<14} {certo}/{total}  ({100*certo/total:5.1f}%)")
            for cod, esp, obt in erros:
                print(f"      {cod}: esperado={esp!r} obtido={obt!r}")
        else:
            print(f"\n  {c:<14} (nada preenchido no gabarito)")

    tot_c = sum(c for c, _ in resumo.values())
    tot_t = sum(t for _, t in resumo.values())
    if tot_t:
        print(f"\n  {'-'*40}\n  ACERTO GERAL: {tot_c}/{tot_t} ({100*tot_c/tot_t:.1f}%)\n")


if __name__ == "__main__":
    main()
