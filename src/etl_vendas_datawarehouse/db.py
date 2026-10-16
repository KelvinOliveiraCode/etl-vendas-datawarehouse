"""Conexao, esquema e verificacao de integridade do DW SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_tempo (
    tempo_id        INTEGER PRIMARY KEY,
    data            TEXT    NOT NULL UNIQUE,
    ano             INTEGER NOT NULL,
    mes             INTEGER NOT NULL,
    dia             INTEGER NOT NULL,
    trimestre       INTEGER NOT NULL,
    dia_da_semana   TEXT    NOT NULL,
    fim_de_semana   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_cliente (
    cliente_id INTEGER PRIMARY KEY,
    nome       TEXT    NOT NULL,
    cidade     TEXT    NOT NULL,
    estado     TEXT    NOT NULL,
    segmento   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_produto (
    produto_id     INTEGER PRIMARY KEY,
    nome           TEXT    NOT NULL,
    categoria      TEXT    NOT NULL,
    preco_unitario REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS fato_vendas (
    venda_id    INTEGER PRIMARY KEY,
    tempo_id    INTEGER NOT NULL,
    cliente_id  INTEGER NOT NULL,
    produto_id  INTEGER NOT NULL,
    quantidade  INTEGER NOT NULL,
    valor_total REAL    NOT NULL,
    FOREIGN KEY (tempo_id)    REFERENCES dim_tempo(tempo_id),
    FOREIGN KEY (cliente_id)  REFERENCES dim_cliente(cliente_id),
    FOREIGN KEY (produto_id)  REFERENCES dim_produto(produto_id)
);
"""

TABLES: tuple[str, ...] = ("dim_tempo", "dim_cliente", "dim_produto", "fato_vendas")


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Abre conexao SQLite com chaves estrangeiras ativadas."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Cria as tabelas do modelo estrela quando ainda nao existirem."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def clear_tables(conn: sqlite3.Connection) -> None:
    """Remove todas as linhas respeitando a ordem das chaves estrangeiras."""
    for table in reversed(TABLES):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


def insert_rows(
    conn: sqlite3.Connection,
    table: str,
    columns: list[str],
    rows: list[tuple],
) -> int:
    """Insere linhas numa tabela e retorna a quantidade inserida."""
    placeholders = ", ".join("?" for _ in columns)
    colunas = ", ".join(columns)
    conn.executemany(
        f"INSERT INTO {table} ({colunas}) VALUES ({placeholders})",
        rows,
    )
    conn.commit()
    return len(rows)


def table_count(conn: sqlite3.Connection, table: str) -> int:
    """Retorna o numero de linhas de uma tabela."""
    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
    return int(cur.fetchone()[0])


def foreign_key_check(conn: sqlite3.Connection) -> list[tuple]:
    """Executa PRAGMA foreign_key_check; vazio significa integridade OK."""
    return conn.execute("PRAGMA foreign_key_check").fetchall()


def verify_integrity(conn: sqlite3.Connection) -> dict[str, object]:
    """Verifica integridade referencial e retorna contagens por tabela."""
    violations = foreign_key_check(conn)
    counts = {table: table_count(conn, table) for table in TABLES}
    return {"ok": len(violations) == 0, "violations": violations, "counts": counts}
