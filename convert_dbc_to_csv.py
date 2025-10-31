#!/usr/bin/env python3
# Converte texto no formato "chave valor ... chave valor ..." para CSV
# e mantém fallback simples para DBC binário (não recomendado para DATASUS real).
# Uso:
# python convert_dbc_to_csv.py entrada.DBC saida.csv [--sep ;] [--keys "nome,id,idade,peso,altura"]

import argparse
import os
import sys
import csv

DEFAULT_KEYS = ["nome", "id", "idade", "peso", "altura"]

def decode_bytes(b: bytes) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    # último recurso
    return b.decode("latin-1", errors="replace")

def parse_text_records(text: str, keys=None):
    """
    Faz parsing de uma ou mais linhas onde cada linha tem pares 'chave valor...'.
    - Junta valores com múltiplas palavras até encontrar a próxima chave.
    - Retorna (header_list, rows_list) onde rows_list é lista de listas.
    """
    key_set = [k.strip().lower() for k in (keys or DEFAULT_KEYS) if k.strip()]
    key_lookup = set(key_set)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None

    records = []
    header_order = []

    for ln in lines:
        tokens = ln.split()
        if not tokens:
            continue

        rec_map = {}
        current_key = None
        for tok in tokens:
            tkl = tok.lower()
            if tkl in key_lookup:
                current_key = tkl
                if current_key not in rec_map:
                    rec_map[current_key] = []
                if current_key not in header_order:
                    header_order.append(current_key)
            else:
                if current_key is None:
                    # Ignora tokens antes da primeira chave
                    continue
                rec_map[current_key].append(tok)

        # Converte listas de tokens em strings (preserva espaços e unidades
        rec = {k: (" ".join(v).strip() if v else "") for k, v in rec_map.items()}

        # Se não encontrou nenhuma chave nessa linha, considera falha
        if not rec:
            return None

        records.append(rec)

    # Cabeçalho: ordem global de primeira aparição
    header = header_order

    # Monta linhas do CSV alinhadas ao cabeçalho
    rows = []
    for rec in records:
        rows.append([rec.get(h, "") for h in header])

    return header, rows

def read_dbc_binary_fallback(path):
    # Fallback mínimo (não serve para DBC real do DATASUS, apenas para não quebrar)
    with open(path, "rb") as f:
        content = f.read()
    if len(content) <= 512:
        return []
    data = content[512:]
    record_size = 144
    records = []
    for i in range(0, len(data), record_size):
        rb = data[i:i+record_size]
        if not rb:
            continue
        # divide em blocos de 8 bytes como string latin-1
        rec = [rb[j:j+8].decode("latin-1", errors="replace").rstrip() for j in range(0, len(rb), 8)]
        records.append(rec)
    return records

def main():
    ap = argparse.ArgumentParser(description="Converte texto 'chave valor ...' para CSV (e tem fallback simples para DBC binário).")
    ap.add_argument("input", help="arquivo de entrada (texto ou binário)")
    ap.add_argument("output", nargs="?", help="arquivo CSV de saída")
    ap.add_argument("--sep", default=";", help="separador CSV (padrão ;)")
    ap.add_argument("--keys", default=",".join(DEFAULT_KEYS), help="lista de chaves separadas por vírgula")
    args = ap.parse_args()

    in_path = args.input
    out_path = args.output or os.path.splitext(in_path)[0] + ".csv"

    if not os.path.exists(in_path):
        sys.exit(f"Arquivo não encontrado: {in_path}")

    # Lê bytes e tenta tratar como texto primeiro
    with open(in_path, "rb") as f:
        b = f.read()

    text = decode_bytes(b)
    # Heurística: se for majoritariamente texto, tenta parser textual
    printable = sum(1 for ch in text if 32 <= ord(ch) <= 126 or ch in "\t\r\n")
    if len(text) > 0 and printable / max(1, len(text)) > 0.6:
        keys = [k.strip() for k in args.keys.split(",")] if args.keys else DEFAULT_KEYS
        parsed = parse_text_records(text, keys=keys)
        if parsed:
            header, rows = parsed
            # Garante diretório e sobrescreve CSV
            out_dir = os.path.dirname(out_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=args.sep)
                w.writerow(header)
                for r in rows:
                    w.writerow(r)
            print(f"Convertido como texto. CSV sobrescrito em: {out_path}")
            return
        # Se falhar parsing textual, cai no fallback binário

    # Fallback binário simples (não é um conversor DBC real)
    records = read_dbc_binary_fallback(in_path)
    if not records:
        print("Não foi possível interpretar o arquivo como texto 'chave valor' nem extrair registros binários.")
        sys.exit(1)

    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=args.sep)
        for rec in records:
            w.writerow(rec)

    print(f"Convertido no modo binário (fallback). CSV sobrescrito em: {out_path}")

if __name__ == "__main__":
    main()