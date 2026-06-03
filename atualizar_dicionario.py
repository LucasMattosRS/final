"""
atualizar_dicionario.py

Roda automaticamente apos o main.py e:
  1. Le tokens_nao_reconhecidos.log
  2. Mostra cada token com o melhor match e score
  3. Pergunta: adicionar ao dicionario.json? (s/n/renomear)
  4. Salva dicionario.json atualizado

Uso:
    python atualizar_dicionario.py            # modo interativo (pergunta um a um)
    python atualizar_dicionario.py --auto     # adiciona tudo com score < 70 automaticamente
    python atualizar_dicionario.py --listar   # so mostra, nao altera nada
"""

import json
import os
import re
import sys
import argparse
from rapidfuzz import process as fuzz_process

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
LOG_PATH       = os.path.join(BASE_DIR, "logs", "tokens_nao_reconhecidos.log")
DICIONARIO_PATH = os.path.join(BASE_DIR, "dicionario.json")


# ── Carregar dicionario atual ─────────────────────────────────────────────────

def carregar_dicionario() -> list[str]:
    if os.path.exists(DICIONARIO_PATH):
        with open(DICIONARIO_PATH, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, list):
            return dados
        if isinstance(dados, dict):
            return dados.get("dicionario", [])
    return []


def salvar_dicionario(dicionario: list[str]) -> None:
    # Ordena e remove duplicatas antes de salvar
    limpo = sorted(set(t.strip() for t in dicionario if t.strip()))
    with open(DICIONARIO_PATH, "w", encoding="utf-8") as f:
        json.dump(limpo, f, ensure_ascii=False, indent=2)
    print(f"\nDicionario salvo em: {DICIONARIO_PATH} ({len(limpo)} entradas)")


# ── Ler log de tokens desconhecidos ──────────────────────────────────────────

def ler_tokens_log() -> list[dict]:
    """
    Le o log e retorna lista de dicts:
      { token, contexto, melhor_match, score }
    """
    if not os.path.exists(LOG_PATH):
        print(f"Log nao encontrado: {LOG_PATH}")
        print("Execute main.py primeiro para gerar o log.")
        return []

    tokens = []
    vistos = set()

    # Formato da linha: DESCONHECIDO | TOKEN | contexto: POSTE-P3 | melhor match: 'CE4' (87%)
    RE = re.compile(
        r"DESCONHECIDO \| (.+?) \| contexto: (.+?)(?:\s*\|\s*melhor match: '(.+?)' \((\d+(?:\.\d+)?)%\))?$"
    )

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            m = RE.match(linha)
            if not m:
                continue
            token    = m.group(1).strip()
            contexto = m.group(2).strip()
            match    = m.group(3) or ""
            score    = float(m.group(4)) if m.group(4) else 0.0

            chave = token.upper()
            if chave in vistos:
                continue
            vistos.add(chave)

            tokens.append({
                "token":        token,
                "contexto":     contexto,
                "melhor_match": match,
                "score":        score,
            })

    return tokens


# ── Modo interativo ───────────────────────────────────────────────────────────

def modo_interativo(tokens: list[dict], dicionario: list[str]) -> list[str]:
    adicionados = 0
    ignorados   = 0

    print(f"\n{'='*60}")
    print(f"  {len(tokens)} token(s) desconhecido(s) encontrado(s)")
    print(f"{'='*60}")
    print("  Comandos: [s] adicionar | [n] ignorar | [r] renomear | [q] sair\n")

    for i, item in enumerate(tokens, 1):
        token    = item["token"]
        match    = item["melhor_match"]
        score    = item["score"]
        contexto = item["contexto"]

        # Indica nivel de confianca do match
        if score >= 85:
            conf = "PROVAVELMENTE ERRO DE OCR"
        elif score >= 70:
            conf = "pode ser erro de OCR"
        else:
            conf = "token novo / desconhecido"

        print(f"[{i}/{len(tokens)}] Token: '{token}'")
        print(f"         Contexto: {contexto}")
        if match:
            print(f"         Melhor match: '{match}' ({score:.0f}%) — {conf}")
        else:
            print(f"         Sem match no dicionario")

        while True:
            resp = input("  > ").strip().lower()
            if resp in ("s", ""):
                dicionario.append(token)
                print(f"  + Adicionado: '{token}'")
                adicionados += 1
                break
            elif resp == "n":
                print(f"  - Ignorado")
                ignorados += 1
                break
            elif resp == "r":
                novo = input("  Novo valor: ").strip()
                if novo:
                    dicionario.append(novo)
                    print(f"  + Adicionado como: '{novo}'")
                    adicionados += 1
                break
            elif resp == "q":
                print("\nSaindo sem salvar o restante.")
                return dicionario
            else:
                print("  Opcoes: s (adicionar), n (ignorar), r (renomear), q (sair)")
        print()

    print(f"\nResumo: {adicionados} adicionado(s), {ignorados} ignorado(s)")
    return dicionario


# ── Modo automatico ───────────────────────────────────────────────────────────

def modo_auto(tokens: list[dict], dicionario: list[str]) -> list[str]:
    """
    Adiciona automaticamente tokens com score < 70
    (provavelmente tokens novos, nao erros de OCR de algo ja no dicionario).
    Tokens com score >= 70 sao listados para revisao manual.
    """
    adicionados  = []
    para_revisar = []

    for item in tokens:
        if item["score"] < 70:
            dicionario.append(item["token"])
            adicionados.append(item["token"])
        else:
            para_revisar.append(item)

    print(f"\n[AUTO] {len(adicionados)} token(s) adicionado(s) automaticamente:")
    for t in adicionados:
        print(f"  + {t}")

    if para_revisar:
        print(f"\n[REVISAR MANUALMENTE] {len(para_revisar)} token(s) com match alto (possivel erro OCR):")
        for item in para_revisar:
            print(f"  ? '{item['token']}' — melhor match: '{item['melhor_match']}' ({item['score']:.0f}%)")
        print("\nRode sem --auto para decidir esses manualmente.")

    return dicionario


# ── Modo listar ───────────────────────────────────────────────────────────────

def modo_listar(tokens: list[dict]) -> None:
    print(f"\n{'='*60}")
    print(f"  {len(tokens)} token(s) desconhecido(s) no log")
    print(f"{'='*60}\n")
    for item in tokens:
        score_str = f"({item['score']:.0f}%)" if item['melhor_match'] else ""
        match_str = f"→ melhor match: '{item['melhor_match']}' {score_str}" if item['melhor_match'] else "→ sem match"
        print(f"  {item['token']:30s} {match_str}  [contexto: {item['contexto']}]")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Atualiza dicionario.json a partir do log de tokens.")
    parser.add_argument("--auto",   action="store_true", help="Adiciona tokens novos automaticamente")
    parser.add_argument("--listar", action="store_true", help="So lista, nao altera o dicionario")
    args = parser.parse_args()

    tokens     = ler_tokens_log()
    dicionario = carregar_dicionario()

    if not tokens:
        print("Nenhum token desconhecido no log. Tudo certo!")
        return

    # Filtra tokens que ja estao no dicionario
    dic_upper  = {t.upper() for t in dicionario}
    tokens_novos = [t for t in tokens if t["token"].upper() not in dic_upper]

    if not tokens_novos:
        print(f"Todos os {len(tokens)} token(s) do log ja estao no dicionario.")
        return

    if args.listar:
        modo_listar(tokens_novos)
        return

    if args.auto:
        dicionario = modo_auto(tokens_novos, dicionario)
    else:
        dicionario = modo_interativo(tokens_novos, dicionario)

    salvar_dicionario(dicionario)

    # Limpa o log apos processar (opcional - comenta se preferir manter historico)
    open(LOG_PATH, "w").close()
    print("Log de tokens limpo para a proxima execucao.")


if __name__ == "__main__":
    main()
