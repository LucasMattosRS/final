"""
precisao/gabarito.py
────────────────────
Gera precisao/gabarito.csv a partir da saída atual, JÁ preenchendo as colunas
de identidade (obra/folha/tipo/codigo) e deixando as colunas de valor EM BRANCO
para você preencher à mão com o valor CORRETO (lido da planta).

Depois de preencher, rode `python -m precisao.medir` para ver o % de acerto.

⚠️ Não sobrescreve um gabarito já preenchido: se gabarito.csv existir, ele cria
   gabarito_novo.csv para você comparar/mesclar manualmente.

Uso:
    python -m precisao.gabarito
"""
import os
import csv

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "saida_atual.csv")
GAB = os.path.join(AQUI, "gabarito.csv")

ID_COLS = ["obra", "folha", "tipo", "codigo"]
VAL_COLS = ["logradouro", "ancoragem", "lado_forte",
            "metragem", "material", "altura_poste"]


def main():
    if not os.path.exists(SAIDA):
        print("Rode primeiro: python -m precisao.rodar")
        return

    with open(SAIDA, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))

    destino = GAB
    if os.path.exists(GAB):
        destino = os.path.join(AQUI, "gabarito_novo.csv")
        print(f"gabarito.csv já existe — gravando em {os.path.basename(destino)} "
              f"para não apagar seu trabalho.")

    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ID_COLS + VAL_COLS)
        w.writeheader()
        for ln in linhas:
            linha = {c: ln.get(c, "") for c in ID_COLS}
            for c in VAL_COLS:
                linha[c] = ""  # você preenche com o valor correto
            w.writerow(linha)

    print(f"Modelo gerado: {destino}")
    print(f"  → {len(linhas)} linhas. Preencha as colunas {VAL_COLS} com o valor")
    print("    CORRETO de cada poste/vão e salve. Linhas que não conseguir conferir,")
    print("    deixe em branco (serão ignoradas na medição).")


if __name__ == "__main__":
    main()
