#!/usr/bin/env python3
# Converte .DBC (DATASUS) para .CSV usando apenas Python puro
# Uso:
#   python convert_dbc_to_csv.py "entrada.DBC" "saida.csv"

import argparse
import os
import sys
import csv

def read_dbc_binary(path):
    """
    Lê um arquivo .DBC do DATASUS como binário.
    Retorna uma lista de registros, cada registro como lista de bytes convertidos para string.
    OBS: isso funciona melhor para arquivos simples; não decodifica tipos complexos.
    """
    with open(path, "rb") as f:
        content = f.read()

    # Remove cabeçalho (os 512 primeiros bytes geralmente são cabeçalho)
    data = content[512:]

    # Cada registro do DATASUS tem tamanho fixo. Normalmente 144 bytes (pode variar)
    record_size = 144
    records = []

    for i in range(0, len(data), record_size):
        record_bytes = data[i:i+record_size]
        # Converte bytes para string latin-1 e divide campos fixos (exemplo genérico)
        record = [record_bytes[j:j+8].decode("latin-1").strip() for j in range(0, len(record_bytes), 8)]
        records.append(record)

    return records

def main():
    parser = argparse.ArgumentParser(description="Converter .DBC (DATASUS) para .CSV sem instalar nada")
    parser.add_argument("input", help="caminho do arquivo .DBC")
    parser.add_argument("output", nargs="?", help="arquivo .CSV de saída (opcional)")
    parser.add_argument("--sep", default=";", help="separador CSV (padrão ;)")
    args = parser.parse_args()

    in_path = args.input
    out_path = args.output or os.path.splitext(in_path)[0] + ".csv"

    if not os.path.exists(in_path):
        sys.exit(f"Arquivo não encontrado: {in_path}")

    print(f"Lendo DBC binário: {in_path}")
    records = read_dbc_binary(in_path)

    print(f"Salvando CSV: {out_path}")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=args.sep)
        for rec in records:
            writer.writerow(rec)

    print("Concluído.")

if __name__ == "__main__":
    main()




    