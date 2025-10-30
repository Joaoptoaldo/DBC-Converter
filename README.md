# Conversor de arquivos DATASUS (.DBC) para CSV

 Ferramenta simples em **Python puro** para converter arquivos **.DBC** do **DATASUS** (como SIH, SINASC, SIM, etc.) em **.CSV** legível, sem depender de bibliotecas externas.

---

## Funcionalidades

- Converte arquivos `.DBC` (binários do DATASUS) em `.CSV`
- Não requer instalação de bibliotecas extras
- Código simples, leve e multiplataforma
- Suporte a separador personalizado (por padrão `;`)

---

##  Como usar

### 1 - Clonar o repositório

        git clone https://github.com/Joaoptoaldo/DBC-Converter.git
        cd DBC-Converter

### 2 - Executar o script

        python convert_dbc_to_csv.py entrada.DBC saida.csv

Parâmetros opcionais:

        --sep ","       # Define o separador do CSV (padrão é ;)

### 3 - Exemplo

        python convert_dbc_to_csv.py SIH.DBC SIH.csv
        

## Estrutura 

        DBC-Converter/
        │
        ├── convert_dbc_to_csv.py   # Script principal
        ├── exemplo/                # (Opcional) Pasta com arquivos de teste
        └── README.md
