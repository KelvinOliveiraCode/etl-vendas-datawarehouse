"""Pipeline ETL: extrai vendas de CSV, carrega DW SQLite (modelo estrela)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pandas as pd

from .db import (
    clear_tables,
    connect,
    create_schema,
    insert_rows,
    verify_integrity,
)

DEFAULT_DB_PATH: Final[Path] = Path("datawarehouse.db")

CSV_COLUMNS: Final[list[str]] = [
    "venda_id",
    "data",
    "cliente_nome",
    "cliente_cidade",
    "cliente_estado",
    "cliente_segmento",
    "produto_nome",
    "produto_categoria",
    "produto_preco_unitario",
    "quantidade",
]

TEMPO_COLUMNS: Final[list[str]] = [
    "tempo_id",
    "data",
    "ano",
    "mes",
    "dia",
    "trimestre",
    "dia_da_semana",
    "fim_de_semana",
]
CLIENTE_COLUMNS: Final[list[str]] = [
    "cliente_id",
    "nome",
    "cidade",
    "estado",
    "segmento",
]
PRODUTO_COLUMNS: Final[list[str]] = [
    "produto_id",
    "nome",
    "categoria",
    "preco_unitario",
]
FATO_COLUMNS: Final[list[str]] = [
    "venda_id",
    "tempo_id",
    "cliente_id",
    "produto_id",
    "quantidade",
    "valor_total",
]

_INT_COLUMNS: Final[set[str]] = {
    "tempo_id",
    "ano",
    "mes",
    "dia",
    "trimestre",
    "fim_de_semana",
    "cliente_id",
    "produto_id",
    "venda_id",
    "quantidade",
}
_FLOAT_COLUMNS: Final[set[str]] = {"preco_unitario", "valor_total"}

_DIAS_SEMANA: Final[list[str]] = [
    "segunda-feira",
    "terca-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sabado",
    "domingo",
]


@dataclass(frozen=True)
class ETLResult:
    """Resultado da execucao do pipeline ETL."""

    db_path: Path
    dim_tempo_rows: int
    dim_cliente_rows: int
    dim_produto_rows: int
    fato_vendas_rows: int


def extract(csv_path: str | Path) -> pd.DataFrame:
    """Le o CSV de vendas e valida as colunas esperadas.

    Levanta ``FileNotFoundError`` quando o arquivo nao existe e
    ``ValueError`` quando faltam colunas obrigatorias.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV de vendas nao encontrado: {path}")
    df = pd.read_csv(path, dtype={"venda_id": "int64", "quantidade": "int64"})
    missing = [coluna for coluna in CSV_COLUMNS if coluna not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes no CSV: {missing}")
    return df


def _dim_tempo(df: pd.DataFrame) -> pd.DataFrame:
    """Gera a dimensao tempo a partir das datas de venda."""
    datas = (
        pd.to_datetime(df["data"], format="%Y-%m-%d")
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )
    tempo = pd.DataFrame({"data": datas.dt.strftime("%Y-%m-%d")})
    tempo["ano"] = tempo["data"].str.slice(0, 4).astype("int64")
    tempo["mes"] = tempo["data"].str.slice(5, 7).astype("int64")
    tempo["dia"] = tempo["data"].str.slice(8, 10).astype("int64")
    datas_dt = pd.to_datetime(tempo["data"])
    tempo["trimestre"] = datas_dt.dt.quarter.astype("int64")
    tempo["dia_da_semana"] = datas_dt.dt.dayofweek.map(
        lambda d: _DIAS_SEMANA[int(d)]
    )
    tempo["fim_de_semana"] = (datas_dt.dt.dayofweek >= 5).astype("int64")
    tempo.insert(0, "tempo_id", range(1, len(tempo) + 1))
    return tempo[TEMPO_COLUMNS]


def _dim_cliente(df: pd.DataFrame) -> pd.DataFrame:
    """Gera a dimensao cliente desduplicada, ordenada de forma deterministica."""
    cols = ["cliente_nome", "cliente_cidade", "cliente_estado", "cliente_segmento"]
    dim = df[cols].drop_duplicates().sort_values(cols).reset_index(drop=True)
    dim.insert(0, "cliente_id", range(1, len(dim) + 1))
    dim.columns = CLIENTE_COLUMNS
    return dim


def _dim_produto(df: pd.DataFrame) -> pd.DataFrame:
    """Gera a dimensao produto desduplicada, ordenada de forma deterministica."""
    cols = ["produto_nome", "produto_categoria", "produto_preco_unitario"]
    dim = df[cols].drop_duplicates().sort_values(cols).reset_index(drop=True)
    dim.insert(0, "produto_id", range(1, len(dim) + 1))
    dim.columns = PRODUTO_COLUMNS
    return dim


def _fato_vendas(
    df: pd.DataFrame,
    dim_tempo: pd.DataFrame,
    dim_cliente: pd.DataFrame,
    dim_produto: pd.DataFrame,
) -> pd.DataFrame:
    """Monta a tabela fato com chaves estrangeiras e valor total da venda."""
    trabalho = df.copy()
    trabalho["data"] = (
        pd.to_datetime(trabalho["data"], format="%Y-%m-%d")
        .dt.strftime("%Y-%m-%d")
    )
    trabalho["valor_total"] = (
        trabalho["quantidade"].astype("int64")
        * trabalho["produto_preco_unitario"].astype("float64")
    )

    tempo_map = dict(
        zip(dim_tempo["data"], dim_tempo["tempo_id"], strict=True)
    )
    cliente_map = dict(
        zip(
            zip(
                dim_cliente["nome"],
                dim_cliente["cidade"],
                dim_cliente["estado"],
                dim_cliente["segmento"],
                strict=True,
            ),
            dim_cliente["cliente_id"],
            strict=True,
        )
    )
    produto_map = dict(
        zip(
            zip(
                dim_produto["nome"],
                dim_produto["categoria"],
                dim_produto["preco_unitario"],
                strict=True,
            ),
            dim_produto["produto_id"],
            strict=True,
        )
    )

    chaves_cliente = list(
        zip(
            trabalho["cliente_nome"],
            trabalho["cliente_cidade"],
            trabalho["cliente_estado"],
            trabalho["cliente_segmento"],
            strict=True,
        )
    )
    chaves_produto = list(
        zip(
            trabalho["produto_nome"],
            trabalho["produto_categoria"],
            trabalho["produto_preco_unitario"],
            strict=True,
        )
    )

    fato = pd.DataFrame(
        {
            "venda_id": trabalho["venda_id"],
            "tempo_id": trabalho["data"].map(tempo_map),
            "cliente_id": pd.Series(chaves_cliente).map(cliente_map),
            "produto_id": pd.Series(chaves_produto).map(produto_map),
            "quantidade": trabalho["quantidade"],
            "valor_total": trabalho["valor_total"],
        }
    )

    incompletos = fato[
        fato[["tempo_id", "cliente_id", "produto_id"]].isna().any(axis=1)
    ]
    if not incompletos.empty:
        raise ValueError(
            "Vendas sem dimensao correspondente: "
            f"{incompletos[['venda_id']].to_dict('records')}"
        )

    fato = fato.sort_values("venda_id").reset_index(drop=True)
    return fato[FATO_COLUMNS]


def transform(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Transforma o extrato bruto nas quatro tabelas do modelo estrela."""
    dim_tempo = _dim_tempo(df)
    dim_cliente = _dim_cliente(df)
    dim_produto = _dim_produto(df)
    fato_vendas = _fato_vendas(df, dim_tempo, dim_cliente, dim_produto)
    return dim_tempo, dim_cliente, dim_produto, fato_vendas


def _rows_native(df: pd.DataFrame, columns: list[str]) -> list[tuple]:
    """Converte linhas do DataFrame para tuplas de tipos nativos do Python."""
    rows: list[tuple] = []
    for record in df[columns].to_dict("records"):
        converted: list = []
        for column in columns:
            value = record[column]
            if column in _INT_COLUMNS:
                converted.append(int(value))
            elif column in _FLOAT_COLUMNS:
                converted.append(float(value))
            else:
                converted.append(str(value))
        rows.append(tuple(converted))
    return rows


def run(
    csv_path: str | Path, db_path: str | Path = DEFAULT_DB_PATH
) -> ETLResult:
    """Executa o pipeline completo: extrai, transforma, carrega e verifica."""
    csv_path = Path(csv_path)
    db_path = Path(db_path)

    df = extract(csv_path)
    dim_tempo, dim_cliente, dim_produto, fato_vendas = transform(df)

    conn = connect(db_path)
    try:
        create_schema(conn)
        clear_tables(conn)
        insert_rows(conn, "dim_tempo", TEMPO_COLUMNS, _rows_native(dim_tempo, TEMPO_COLUMNS))
        insert_rows(
            conn, "dim_cliente", CLIENTE_COLUMNS, _rows_native(dim_cliente, CLIENTE_COLUMNS)
        )
        insert_rows(
            conn,
            "dim_produto",
            PRODUTO_COLUMNS,
            _rows_native(dim_produto, PRODUTO_COLUMNS),
        )
        insert_rows(conn, "fato_vendas", FATO_COLUMNS, _rows_native(fato_vendas, FATO_COLUMNS))

        integridade = verify_integrity(conn)
        if not integridade["ok"]:
            raise RuntimeError(
                f"Integridade referencial violada: {integridade['violations']}"
            )
    finally:
        conn.close()

    return ETLResult(
        db_path=db_path,
        dim_tempo_rows=len(dim_tempo),
        dim_cliente_rows=len(dim_cliente),
        dim_produto_rows=len(dim_produto),
        fato_vendas_rows=len(fato_vendas),
    )
