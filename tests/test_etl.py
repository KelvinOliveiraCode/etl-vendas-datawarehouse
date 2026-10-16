"""Suite de testes do pipeline ETL de vendas (modelo estrela, SQLite)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from etl_vendas_datawarehouse.db import connect, verify_integrity
from etl_vendas_datawarehouse.etl import (
    CSV_COLUMNS,
    extract,
    run,
    transform,
)

CSV_HEADER = ",".join(CSV_COLUMNS)

LINHA_1 = "1,2024-01-10,Ana Silva,Sao Paulo,SP,Varejo,Notebook,Eletronicos,3500.00,2"
LINHA_2 = "2,2024-01-10,Bruno Costa,Rio de Janeiro,RJ,Corporativo,Mouse,Eletronicos,150.00,5"
LINHA_3 = "3,2024-02-15,Ana Silva,Sao Paulo,SP,Varejo,Cadeira,Mobiliario,450.00,1"
LINHA_4 = "4,2024-03-05,Carla Dias,Belo Horizonte,MG,Varejo,Notebook,Eletronicos,3500.00,1"
LINHA_5 = "5,2024-03-05,Bruno Costa,Rio de Janeiro,RJ,Corporativo,Teclado,Eletronicos,220.00,3"


def _grava_csv(tmp_path: Path, linhas: list[str]) -> Path:
    caminho = tmp_path / "vendas.csv"
    caminho.write_text(CSV_HEADER + "\n" + "\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


def test_extract_leva_arquivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract(tmp_path / "nao_existe.csv")


def test_extract_rejeita_colunas_ausentes(tmp_path: Path) -> None:
    caminho = tmp_path / "vendas.csv"
    caminho.write_text(
        "venda_id,data,cliente_nome,cliente_cidade,cliente_estado,cliente_segmento,produto_nome,produto_categoria,produto_preco_unitario\n"
        "1,2024-01-10,Ana,Sao Paulo,SP,Varejo,Notebook,Eletronicos,3500.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Colunas ausentes no CSV"):
        extract(caminho)


def test_etl_carrega_dw_com_modelo_estrela(tmp_path: Path) -> None:
    csv_path = _grava_csv(tmp_path, [LINHA_1, LINHA_2, LINHA_3, LINHA_4, LINHA_5])
    db_path = tmp_path / "dw.db"
    resultado = run(csv_path, db_path)

    assert resultado.fato_vendas_rows == 5
    assert resultado.dim_tempo_rows == 3
    assert resultado.dim_cliente_rows == 3
    assert resultado.dim_produto_rows == 4
    assert db_path.is_file()
    assert resultado.db_path == db_path

    conn = connect(db_path)
    try:
        integridade = verify_integrity(conn)
        assert integridade["ok"] is True
        assert integridade["violations"] == []

        contagens = integridade["counts"]
        assert contagens["fato_vendas"] == 5
        assert contagens["dim_tempo"] == 3
        assert contagens["dim_cliente"] == 3
        assert contagens["dim_produto"] == 4

        # Valor total = quantidade * preco unitario (linha 1: 2 * 3500 = 7000)
        cur = conn.execute("SELECT valor_total FROM fato_vendas WHERE venda_id = 1")
        assert cur.fetchone()[0] == 7000.0

        # Nenhuma venda ora: todo fato referencia dimensoes existentes.
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM fato_vendas f
            LEFT JOIN dim_tempo t ON f.tempo_id = t.tempo_id
            LEFT JOIN dim_cliente c ON f.cliente_id = c.cliente_id
            LEFT JOIN dim_produto p ON f.produto_id = p.produto_id
            WHERE t.tempo_id IS NULL OR c.cliente_id IS NULL OR p.produto_id IS NULL
            """
        )
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_etl_e_deterministico(tmp_path: Path) -> None:
    csv_path = _grava_csv(tmp_path, [LINHA_1, LINHA_2, LINHA_3])
    resultado_um = run(csv_path, tmp_path / "dw_a.db")
    resultado_dois = run(csv_path, tmp_path / "dw_b.db")

    assert (
        resultado_um.dim_tempo_rows,
        resultado_um.dim_cliente_rows,
        resultado_um.dim_produto_rows,
        resultado_um.fato_vendas_rows,
    ) == (
        resultado_dois.dim_tempo_rows,
        resultado_dois.dim_cliente_rows,
        resultado_dois.dim_produto_rows,
        resultado_dois.fato_vendas_rows,
    )


def test_transform_gera_tabelas_esperadas() -> None:
    df = pd.DataFrame(
        [
            [
                1,
                "2024-01-10",
                "Ana",
                "Sao Paulo",
                "SP",
                "Varejo",
                "Notebook",
                "Eletronicos",
                3500.0,
                2,
            ],
        ],
        columns=CSV_COLUMNS,
    )
    dim_tempo, dim_cliente, dim_produto, fato = transform(df)

    assert list(dim_tempo.columns) == [
        "tempo_id",
        "data",
        "ano",
        "mes",
        "dia",
        "trimestre",
        "dia_da_semana",
        "fim_de_semana",
    ]
    assert len(dim_tempo) == 1
    assert int(dim_tempo.iloc[0]["tempo_id"]) == 1
    assert str(dim_tempo.iloc[0]["data"]) == "2024-01-10"
    assert int(dim_tempo.iloc[0]["ano"]) == 2024
    assert int(dim_tempo.iloc[0]["mes"]) == 1
    assert int(dim_tempo.iloc[0]["dia"]) == 10
    assert int(dim_tempo.iloc[0]["trimestre"]) == 1
    assert str(dim_tempo.iloc[0]["dia_da_semana"]) == "quarta-feira"
    assert int(dim_tempo.iloc[0]["fim_de_semana"]) == 0

    assert list(dim_cliente.columns) == [
        "cliente_id",
        "nome",
        "cidade",
        "estado",
        "segmento",
    ]
    assert len(dim_cliente) == 1

    assert list(dim_produto.columns) == [
        "produto_id",
        "nome",
        "categoria",
        "preco_unitario",
    ]
    assert len(dim_produto) == 1

    assert list(fato.columns) == [
        "venda_id",
        "tempo_id",
        "cliente_id",
        "produto_id",
        "quantidade",
        "valor_total",
    ]
    assert len(fato) == 1
    assert int(fato.iloc[0]["venda_id"]) == 1
    assert int(fato.iloc[0]["quantidade"]) == 2
    assert float(fato.iloc[0]["valor_total"]) == 7000.0


def test_cli_executa(tmp_path: Path) -> None:
    from etl_vendas_datawarehouse.cli import main

    csv_path = _grava_csv(tmp_path, [LINHA_1])
    db_path = tmp_path / "dw.db"
    codigo = main([str(csv_path), "--db", str(db_path)])
    assert codigo == 0
    assert db_path.is_file()
