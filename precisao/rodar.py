"""
precisao/rodar.py
─────────────────
Roda o pipeline em TODOS os PDFs de input_pdf/ e:
  1. Salva a saída consolidada em precisao/saida_atual.csv
  2. Imprime indicadores de qualidade (proxies) que NÃO dependem de gabarito:
       - taxa de preenchimento de cada coluna
       - nº de tokens "fragmentados" (1 caractere) e "grudados" (muito longos)
       - nº de tokens não reconhecidos pelo dicionário

Use isto ANTES e DEPOIS de qualquer mudança para comparar o efeito.
Uso:
    python -m precisao.rodar
"""
import os
import csv
import sys
import logging

# permite rodar tanto como módulo quanto direto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.disable(logging.CRITICAL)  # silencia o pipeline durante a medição

from config import INPUT_DIR  # noqa: E402
from main import process_pdf, group_pdfs_by_obra  # noqa: E402

SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saida_atual.csv")

COLUNAS = [
    "obra", "folha", "tipo", "codigo",
    "logradouro", "ancoragem", "lado_forte",
    "metragem", "material", "altura_poste",
    "informacoes", "confianca", "status",
]

# colunas de "valor" cuja qualidade nos interessa medir
COLS_VALOR = ["logradouro", "ancoragem", "lado_forte",
              "metragem", "material", "altura_poste"]


def _qualidade_tokens(informacoes_concat: str) -> dict:
    """Conta fragmentos e grudados na coluna de informações (proxy de ruído)."""
    tokens = []
    for bloco in informacoes_concat.split("|"):
        tokens.extend(t for t in bloco.split() if t)
    frag = sum(1 for t in tokens if len(t) == 1)
    grud = sum(1 for t in tokens if len(t) >= 25)  # cadeias enormes = grudado
    return {"tokens": len(tokens), "frag": frag, "grud": grud}


def main():
    limite = int(sys.argv[1]) if len(sys.argv) > 1 else None
    grupos = group_pdfs_by_obra(INPUT_DIR)
    linhas = []
    obras = list(grupos.items())
    if limite:
        obras = obras[:limite]
    for obra, pdfs in obras:
        for pdf in pdfs:
            try:
                linhas.extend(process_pdf(pdf))
            except Exception as e:  # noqa: BLE001
                print(f"  ! erro em {os.path.basename(pdf)}: {e}", file=sys.stderr)

    if not linhas:
        print("Nenhuma linha gerada. Verifique input_pdf/.")
        return

    # grava CSV
    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction="ignore")
        w.writeheader()
        for ln in linhas:
            w.writerow(ln)

    # ── indicadores ───────────────────────────────────────────────────────
    n = len(linhas)
    print(f"\n{'='*56}")
    print(f"  MEDIÇÃO DE QUALIDADE  ({n} linhas, {len(obras)} obras)")
    print(f"{'='*56}")

    print("\n  Taxa de preenchimento por coluna:")
    for c in COLS_VALOR:
        preenchidos = sum(1 for ln in linhas if str(ln.get(c, "")).strip())
        print(f"    {c:<14} {preenchidos:>4}/{n}  ({100*preenchidos/n:5.1f}%)")

    tot = {"tokens": 0, "frag": 0, "grud": 0}
    for ln in linhas:
        q = _qualidade_tokens(str(ln.get("informacoes", "")))
        for k in tot:
            tot[k] += q[k]
    print("\n  Qualidade dos tokens em 'informações':")
    print(f"    total de tokens        : {tot['tokens']}")
    print(f"    fragmentos (1 caractere): {tot['frag']}  "
          f"({100*tot['frag']/max(tot['tokens'],1):.1f}%)")
    print(f"    grudados (>=25 chars)  : {tot['grud']}  "
          f"({100*tot['grud']/max(tot['tokens'],1):.1f}%)")

    conf = [ln.get("confianca", 0) for ln in linhas]
    print(f"\n  Confiança média: {sum(conf)/len(conf):.1f}")
    aprov = sum(1 for ln in linhas if ln.get("status") == "APROVADO")
    print(f"  Aprovados: {aprov}/{n} ({100*aprov/n:.1f}%)")
    print(f"\n  CSV salvo em: {SAIDA}\n")


if __name__ == "__main__":
    main()
