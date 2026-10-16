"""Interface de linha de comando do ETL de vendas."""

from __future__ import annotations

import argparse
from pathlib import Path

from .etl import DEFAULT_DB_PATH, run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="etl-vendas",
        description="Extrai vendas de CSV e carrega DW SQLite com modelo estrela.",
    )
    parser.add_argument("csv", help="Caminho do CSV de entrada")
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help="Caminho do banco SQLite de destino",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    resultado = run(args.csv, Path(args.db))
    print(
        "DW carregado: "
        f"{resultado.fato_vendas_rows} vendas, "
        f"{resultado.dim_tempo_rows} tempos, "
        f"{resultado.dim_cliente_rows} clientes, "
        f"{resultado.dim_produto_rows} produtos em "
        f"{resultado.db_path}"
    )
    return 0
