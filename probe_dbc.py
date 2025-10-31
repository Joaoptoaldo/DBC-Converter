# Uso: python probe_dbc.py entrada.DBC
# ferramenta de diagnóstico para inspecionar um arquivo binário

import sys, os
p = sys.argv[1] if len(sys.argv) > 1 else "entrada.DBC"
if not os.path.exists(p):
    print("Arquivo não existe:", p); sys.exit(1)
b = open(p,"rb").read()
print("Caminho:", p)
print("Tamanho (bytes):", len(b))
print("Primeiros 256 bytes (hex):")
print(b[:256].hex())
print("\nPrimeiros 256 bytes (latin-1):")
print(b[:256].decode("latin-1", errors="replace"))