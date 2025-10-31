#!/usr/bin/env python3
# Converte texto "chave valor ..." para CSV sem precisar listar chaves previamente
# Heurística: uma "chave" é um token composto apenas por letras minúsculas (a-z e acentos).
# Tudo que vier depois vira "valor" até a próxima chave.
# Observação: isso não lê DBC real do DATASUS (binário). Para DBC real, será necessário descompressor.
#
# Uso:
#   python convert_dbc_to_csv.py entrada.DBC saida.csv [--sep ;]
#
# Exemplos de linhas suportadas:
#   nome JOAO PEDRO id 123 idade 21 peso 80kg altura 188cm
#   nome: JOAO PEDRO id: 123 idade: 21 peso: 80kg altura: 188cm
#   nome=JOAO PEDRO id=123 idade=21 peso=80kg altura=188cm
#
# Limitações:
# - Se valores também forem palavras minúsculas (ex: "nome joao pedro"), a heurística pode confundir.
#   Nesse caso, prefira "nome: joao pedro" ou "nome=joao pedro" para remover ambiguidade.

import argparse
import os
import sys
import csv
import re

LOWER_WORD_RE = re.compile(r"^[a-zà-öø-ÿ]+$")  # token inteiramente minúsculo com acentos

def decode_bytes(b):
    for enc in ("utf-8", "latin-1"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("latin-1", errors="replace")

def tokenize_with_pairs(line: str):
    """
    Normaliza pares explícitos "chave: valor" ou "chave=valor" em tokens [chave, valor...].
    Retorna lista de tokens (strings) preservando ordem e espaços em valores via pós-processamento.
    """
    # Primeiro, padroniza ":" e "=" inserindo espaço para separar chave do valor
    # Ex.: "nome:JOAO" -> "nome : JOAO", "id=123" -> "id = 123"
    line = re.sub(r":", " : ", line)
    line = re.sub(r"=", " = ", line)
    # Agora quebra em tokens simples (por espaços)
    return line.split()

def parse_line_guess_pairs(line: str):
    """
    Aplica duas estratégias:
    1) Se existirem pares explícitos com ':' ou '=', usa-os como delimitadores.
       Ex.: 'nome: JOAO PEDRO id: 123' -> chaves 'nome','id' com valores apropriados.
    2) Caso contrário, usa heurística de 'chave = token minúsculo' e agrega valores até a próxima chave minúscula.
    Retorna (ordered_keys, values_in_same_order) ou None se não achar nenhuma chave.
    """
    tokens = tokenize_with_pairs(line)

    # Estratégia 1: pares explícitos com ":" ou "="
    if ":" in tokens or "=" in tokens:
        rec = {}
        order = []
        i = 0
        current_key = None
        value_buf = []
        while i < len(tokens):
            t = tokens[i]
            if t in (":", "=") and current_key is not None:
                # apenas ignora o separador, pois já estamos coletando valor
                i += 1
                continue
            # Chave candidata antes de ":" ou "="
            if i + 1 < len(tokens) and tokens[i+1] in (":", "="):
                # Se havia uma chave anterior, fecha o valor acumulado
                if current_key is not None:
                    rec[current_key] = " ".join(value_buf).strip()
                    value_buf = []
                current_key = tokens[i].strip().lower()
                if current_key not in rec:
                    order.append(current_key)
                i += 2  # pula "key" e ":"/"="
                continue
            # Caso geral: acumula no valor
            if current_key is not None:
                value_buf.append(t)
            i += 1
        # Fecha último valor
        if current_key is not None:
            rec[current_key] = " ".join(value_buf).strip()
        if rec:
            return order, [rec.get(k, "") for k in order]

    # Estratégia 2: heurística por minúsculas
    rec = {}
    order = []
    current_key = None
    value_buf = []
    for t in tokens:
        if LOWER_WORD_RE.match(t):
            # se já havia uma chave, fecha o valor anterior
            if current_key is not None:
                rec[current_key] = " ".join(value_buf).strip()
                value_buf = []
            current_key = t
            if current_key not in rec:
                order.append(current_key)
        else:
            if current_key is None:
                # ignora lixo antes da primeira chave
                continue
            value_buf.append(t)
    if current_key is not None:
        rec[current_key] = " ".join(value_buf).strip()

    if not rec:
        return None

    return order, [rec.get(k, "") for k in order]

def parse_text_records(text: str):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    header = []
    rows = []
    for ln in lines:
        parsed = parse_line_guess_pairs(ln)
        if not parsed:
            return None
        keys, vals = parsed
        # Atualiza cabeçalho mantendo ordem global de primeira aparição
        for k in keys:
            if k not in header:
                header.append(k)
        # Realinha vals ao header global
        rec_map = dict(zip(keys, vals))
        rows.append([rec_map.get(h, "") for h in header])
    return header, rows

def is_mostly_text(b: bytes):
    # Heurística simples
    try:
        s = b.decode("utf-8")
        txt = s
    except Exception:
        try:
            s = b.decode("latin-1")
            txt = s
        except Exception:
            return False
    printable = sum(1 for ch in txt if ch == "\n" or ch == "\t" or 32 <= ord(ch) <= 126)
    return printable / max(1, len(txt)) > 0.6

def main():
    ap = argparse.ArgumentParser(description="Converte texto 'chave valor ...' para CSV sem lista de chaves prévia. Para DBC real do DATASUS, é necessário descompressor externo.")
    ap.add_argument("input", help="arquivo de entrada (texto livre ou .dbc)")
    ap.add_argument("output", nargs="?", help="arquivo CSV de saída (sobrescreve)")
    ap.add_argument("--sep", default=";", help="separador CSV (padrão ;)")
    args = ap.parse_args()

    in_path = args.input
    out_path = args.output or os.path.splitext(in_path)[0] + ".csv"

    if not os.path.exists(in_path):
        sys.exit(f"Arquivo não encontrado: {in_path}")

    with open(in_path, "rb") as f:
        b = f.read()

    # 1) Tenta tratar como texto livre
    if is_mostly_text(b):
        text = decode_bytes(b)
        parsed = parse_text_records(text)
        if parsed:
            header, rows = parsed
            out_dir = os.path.dirname(out_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=args.sep)
                w.writerow(header)
                for r in rows:
                    w.writerow(r)
            print(f"Convertido como texto livre. CSV sobrescrito em: {out_path}")
            return
        else:
            print("Arquivo textual, mas não foi possível deduzir pares 'chave valor' sem ambiguidade.")
            print("Dica: use 'chave: valor' ou 'chave=valor' para remover ambiguidade.")
            sys.exit(1)

    # 2) Caso contrário, parece binário (.dbc real provavelmente)
    print("Arquivo parece binário (possível .dbc real do DATASUS).")
    print("- Este script não implementa o descompressor DBC do DATASUS (formato DBF comprimido).")
    print("- Para suportar QUALQUER .dbc real, use um destes caminhos:")
    print("  a) pydatasus (Python) para baixar e ler nativamente;")
    print("  b) usar 'dbc2dbf' (ou ferramenta similar) para descomprimir .dbc -> .dbf e então converter DBF -> CSV;")
    print("  c) posso te fornecer um pipeline/roteiro passo-a-passo e um script que chama a ferramenta e gera o CSV.")
    sys.exit(2)

if __name__ == "__main__":
    main()