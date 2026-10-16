# etl-vendas-datawarehouse

## Português

### Descrição

Pipeline de ETL para data warehouse com modelo estrela. Extrai vendas de um arquivo CSV, carrega um banco SQLite com quatro tabelas — `fato_vendas`, `dim_tempo`, `dim_cliente`, `dim_produto` — e verifica integridade referencial (`PRAGMA foreign_key_check`) antes de concluir.

Stack: Python, pandas, SQLite (sem dependência de servidor externo).

### Como usar

Instale o pacote no modo editável:

```
python -m pip install -e .
```

Execute a extração e carga:

```
python -m etl_vendas_datawarehouse dados/vendas.csv --db dw.db
```

Ou via entry point instalado:

```
etl-vendas dados/vendas.csv --db dw.db
```

O CSV de entrada deve ter as colunas:

```
venda_id,data,cliente_nome,cliente_cidade,cliente_estado,cliente_segmento,produto_nome,produto_categoria,produto_preco_unitario,quantidade
```

Saída esperada (exemplo):

```
DW carregado: 5 vendas, 3 tempos, 3 clientes, 4 produtos em dw.db
```

### Testes

Rode a suíte pytest:

```
python -m pytest -q
```

Resultado esperado:

```
6 passed in 1.25s
```

O teste gera um CSV sintético em diretório temporário, executa o ETL e asserta: contagens de fato e dimensões, `valor_total = quantidade * preco_unitario`, ausência de vendas órfãs e integridade de chaves estrangeiras.

Também há lint:

```
python -m ruff check .
```

### Estrutura

```
etl-vendas-datawarehouse/
  pyproject.toml            # dependências, entry point, config do ruff
  README.md                 # este arquivo
  BRIEF.md                  # resumo de entregas e como verificar
  src/etl_vendas_datawarehouse/
    __init__.py             # versão do pacote
    __main__.py             # permite `python -m etl_vendas_datawarehouse`
    cli.py                  # interface de linha de comando
    db.py                   # conexão, esquema, inserção, verificação de integridade
    etl.py                  # extração, transformação e carga do modelo estrela
  tests/test_etl.py         # suíte pytest
```

### Licença

MIT

### Autor

Kelvin Oliveira

---

## English

### Description

ETL pipeline for a data warehouse with a star model. It extracts sales from a CSV file, loads a SQLite database with four tables — `fato_vendas`, `dim_tempo`, `dim_cliente`, `dim_produto` — and checks referential integrity (`PRAGMA foreign_key_check`) before finishing.

Stack: Python, pandas, SQLite (no external server required).

### How to use

Install the package in editable mode:

```
python -m pip install -e .
```

Run extract and load:

```
python -m etl_vendas_datawarehouse dados/vendas.csv --db dw.db
```

Or via the installed entry point:

```
etl-vendas dados/vendas.csv --db dw.db
```

The input CSV must have these columns:

```
venda_id,data,cliente_nome,cliente_cidade,cliente_estado,cliente_segmento,produto_nome,produto_categoria,produto_preco_unitario,quantidade
```

Expected output (example):

```
DW carregado: 5 vendas, 3 tempos, 3 clientes, 4 produtos em dw.db
```

### Tests

Run the pytest suite:

```
python -m pytest -q
```

Expected result:

```
6 passed in 1.25s
```

The test generates a synthetic CSV in a temporary directory, runs the ETL, and asserts fact and dimension counts, `valor_total = quantity * unit_price`, no orphan sales, and foreign-key integrity.

There is also lint:

```
python -m ruff check .
```

### Structure

```
etl-vendas-datawarehouse/
  pyproject.toml            # dependencies, entry point, ruff config
  README.md                 # this file
  BRIEF.md                  # deliveries summary and how to verify
  src/etl_vendas_datawarehouse/
    __init__.py             # package version
    __main__.py             # allows `python -m etl_vendas_datawarehouse`
    cli.py                  # command-line interface
    db.py                   # connection, schema, insertion, integrity check
    etl.py                  # extract, transform and load of the star model
  tests/test_etl.py         # pytest suite
```

### License

MIT

### Author

Kelvin Oliveira
