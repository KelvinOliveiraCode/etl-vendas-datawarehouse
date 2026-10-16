# BRIEF — etl-vendas-datawarehouse

Projeto: ETL para data warehouse com modelo estrela (área Dados/BI).
Diretório: C:\Users\Kelvin\AppData\Local\Temp\opencode\github-staging\projects\etl-vendas-datawarehouse\

## Entregas

- `pyproject.toml` — dependências (pandas>=2.2.0), entry point `etl-vendas`, config do ruff.
- `src/etl_vendas_datawarehouse/__init__.py` — versão do pacote (0.1.0).
- `src/etl_vendas_datawarehouse/__main__.py` — execução via `python -m etl_vendas_datawarehouse`.
- `src/etl_vendas_datawarehouse/cli.py` — CLI: `etl-vendas <csv> [--db <sqlite>]`.
- `src/etl_vendas_datawarehouse/db.py` — conexão SQLite, esquema, inserção, verificação de integridade (`PRAGMA foreign_key_check`).
- `src/etl_vendas_datawarehouse/etl.py` — ETL: extrai CSV, transforma em modelo estrela (`fato_vendas`, `dim_tempo`, `dim_cliente`, `dim_produto`), carrega e verifica integridade.
- `tests/test_etl.py` — 6 testes pytest: arquivo inexistente, colunas ausentes, carga correta do DW, determinismo, transformação das tabelas, execução da CLI.
- `README.md` — documentação completa bilíngue PT-BR + EN (descrição, como usar, testes, estrutura, licença MIT, autor Kelvin Oliveira).
- `BRIEF.md` — este arquivo.

## Modelo estrela

Tabelas: `dim_tempo`, `dim_cliente`, `dim_produto`, `fato_vendas` (chaves estrangeiras para as três dimensões).
`valor_total = quantidade * preco_unitario` é calculado no ETL e validado nos testes.

## Como verificar

1. Instale o pacote:
   ```
   python -m pip install -e .
   ```
2. Rode o lint:
   ```
   python -m ruff check .
   ```
   Resultado esperado: `All checks passed!`
3. Rode os testes:
   ```
   python -m pytest -q
   ```
   Resultado esperado: `6 passed`
4. Execute o ETL sobre um CSV de vendas:
   ```
   python -m etl_vendas_datawarehouse dados/vendas.csv --db dw.db
   ```

## Critérios de aceitação

- [x] DW carregado corretamente (fato + 3 dimensões, integridade referencial verificada).
- [x] Testes que passem (6 passed).
- [x] README completo em PT-BR e EN.
- [x] Código com tipos, docstrings, sem slop de IA (ruff limpo).

Autor: Kelvin Oliveira — Licença: MIT.
