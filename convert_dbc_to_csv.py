#!/usr/bin/env python3
# Converte .DBC (DATASUS) simples ou arquivos de texto pequenos para .CSV
# Uso:
#   python convert_dbc_to_csv.py entrada.DBC saida.csv

import argparse
import os
import sys
import csv
import re

def try_simple_text_parse(text):
    """
    Tenta extrair pares chave-valor simples de uma linha ou texto curto.
    Exemplo: "nome JOAO id 12345 idade 21" -> header ['nome','id','idade'], values ['JOAO','12345','21']
    Retorna (header_list, values_list) ou None se não conseguir.
    """
    # Normaliza espaços
    s = " ".join(text.split())
    if not s:
        return None

    # Primeiro, tenta extrair pares onde chaves e valores são separados por espaço.
    # tokens: palavras ou números
    tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+|\d+", s)
    if len(tokens) < 2:
        return None

    pairs = []
    i = 0
    while i < len(tokens):
        key = tokens[i]
        # se houver token seguinte, toma como valor
        if i + 1 < len(tokens):
            val = tokens[i+1]
            i += 2
        else:
            # último token sem par: tenta separar letras+dígitos (ex: id12345)
            m = re.match(r"^([A-Za-zÀ-ÖØ-öø-ÿ]+)(\d+)$", key)
            if m:
                key = m.group(1)
                val = m.group(2)
                i += 1
            else:
                return None
        pairs.append((key.strip().lower(), val.strip()))
    # Construir header na ordem de aparição, removendo repetições (mantém última ocorrência)
    header = []
    seen = set()
    for k, v in pairs:
        if k not in seen:
            header.append(k)
            seen.add(k)
    # Map para últimos valores
    d = {}
    for k, v in pairs:
        d[k] = v
    values = [d[h] for h in header]
    return header, values

def read_dbc_binary(path):
    """
    Método conservador para arquivos binários .DBC.
    Aqui deixamos comportamento simples: tenta extrair registros assumindo header de 512 bytes e record_size 144.
    Retorna lista de registros (cada registro é lista de campos).
    """
    with open(path, "rb") as f:
        content = f.read()

    if len(content) <= 512:
        # não há dados binários depois do cabeçalho presumido
        return []

    data = content[512:]
    record_size = 144
    records = []
    for i in range(0, len(data), record_size):
        record_bytes = data[i:i+record_size]
        if not record_bytes:
            continue
        # dividir em fatias de 8 bytes como fallback
        rec = [record_bytes[j:j+8].decode("latin-1", errors="replace").rstrip() for j in range(0, len(record_bytes), 8)]
        records.append(rec)
    return records

def main():
    parser = argparse.ArgumentParser(description="Converter .DBC (DATASUS) ou texto simples para .CSV (sobrescreve saída).")
    parser.add_argument("input", help="caminho do arquivo .DBC (ou arquivo de texto curto)")
    parser.add_argument("output", nargs="?", help="arquivo .CSV de saída (opcional)")
    parser.add_argument("--sep", default=";", help="separador CSV (padrão ;)")
    args = parser.parse_args()

    in_path = args.input
    out_path = args.output or os.path.splitext(in_path)[0] + ".csv"

    if not os.path.exists(in_path):
        sys.exit(f"Arquivo não encontrado: {in_path}")

    # Ler bytes
    with open(in_path, "rb") as f:
        b = f.read()

    size = len(b)
    # Tentar decodificar em latin-1 para análise textual
    try:
        txt = b.decode("latin-1")
    except Exception:
        txt = ""

    printable = sum(1 for ch in txt if 32 <= ord(ch) <= 126)
    printable_ratio = printable / max(1, len(txt))

    # Heurística: se arquivo é pequeno (< 2048 bytes) e majoritariamente texto, tenta parser simples
    if size < 2048 and printable_ratio > 0.6:
        parsed = try_simple_text_parse(txt)
        if parsed:
            header, values = parsed
            # garantir diretório de saída
            out_dir = os.path.dirname(out_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
            # sobrescreve sempre (modo 'w')
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=args.sep)
                writer.writerow(header)
                writer.writerow(values)
            print(f"Arquivo pequeno detectado e convertido para CSV. Saída sobrescrita em: {out_path}")
            return
        else:
            print("Arquivo pequeno e textual, mas não foi possível parsear automaticamente. Conteúdo:")
            print(txt)
            sys.exit(1)

    # Caso contrário, tentar leitura binária (comportamento antigo)
    records = read_dbc_binary(in_path)
    if not records:
        print("Nenhum registro binário extraído. Verifique se o arquivo .DBC está correto.")
        sys.exit(1)

    # garantir diretório de saída
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # Sobrescrever saida.csv com registros extraídos
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=args.sep)
        for rec in records:
            # normaliza campos
            norm = [ (c.replace("\r","").replace("\n","").strip() if isinstance(c, str) else c) for c in rec ]
            writer.writerow(norm)

    print(f"Conversão binária concluída. Saída sobrescrita em: {out_path}")

if __name__ == "__main__":
    main()