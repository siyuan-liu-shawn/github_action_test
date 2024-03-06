#!/usr/bin/env python
# -*- coding: utf-8 -*-
import textwrap
from datetime import datetime

import pytest
from dataplatform_kubernetes import BASE_DIR
from dataplatform_kubernetes.bigquery.schema_history import SchemaHistory
from google.cloud.bigquery import Client, Table


@pytest.fixture
def mock_bigquery_client(mocker):
    mock_bigquery_client = mocker.Mock(spec=Client)
    mocker.patch("dataplatform_kubernetes.bigquery.schema_history.Client", mock_bigquery_client)
    return mock_bigquery_client


class TestSchemaHistory:
    def test_init(self, mock_bigquery_client):
        actual = SchemaHistory(
            env="test",
            dir=BASE_DIR / "bigquery" / "migrations",
            parent_project="test-parent-project",
            project="test-project",
            dataset="test_dataset",
            table="test_table",
        )
        assert actual.env == "test"
        assert actual.dir == BASE_DIR / "bigquery" / "migrations"
        assert actual.parent_project == "test-parent-project"
        assert actual.project == "test-project"
        assert actual.dataset == "test_dataset"
        assert actual.table == "test_table"

        mock_bigquery_client.assert_called_once_with(project="test-parent-project")
        mock_bigquery_client.return_value.create_table.assert_called_once_with(
            Table(
                "test-project.test_dataset.test_table",
                schema=SchemaHistory.schema(),
            ),
            exists_ok=True,
        )

    def test_read_migration_config(self, mock_bigquery_client):
        history = SchemaHistory(
            env="test",
            dir=BASE_DIR / "bigquery" / "migrations",
            parent_project="test-parent-project",
            project="test-project",
            dataset="test_dataset",
            table="test_table",
        )
        actual = history.read_migration_config()
        actual_0 = actual[0]
        assert actual_0.script == "V20210101112233__merpay_dataplatform_jp.sql"
        assert actual_0.version == datetime(2021, 1, 1, 11, 22, 33)
        assert actual_0.description == "merpay_dataplatform_jp"
        assert actual_0.checksum == "2a7d3ee9606e0da7464e899a97b08883"
        assert actual_0.queries == [
            textwrap.dedent(
                """
                UPDATE `kouzoh-p-tomoyuki-nakamura.test.test_table_1`
                SET name = 'update name'
                WHERE id = 1
                """
            ).strip(),
            textwrap.dedent(
                """
                ALTER TABLE `kouzoh-p-tomoyuki-nakamura.test.test_table_2`
                RENAME TO test_table_rename
                """
            ).strip(),
            textwrap.dedent(
                """
                ALTER TABLE `kouzoh-p-tomoyuki-nakamura.test.test_table_3`
                ADD COLUMN add_column STRING
                """
            ).strip(),
        ]
