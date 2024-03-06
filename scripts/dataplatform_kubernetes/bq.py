#!/usr/bin/env python
# -*- coding: utf-8 -*-
import click
from dataplatform_kubernetes import BASE_DIR, ENVIRONMENTS
from dataplatform_kubernetes.bigquery.schema_history import SchemaHistory


@click.group()
def bq() -> None:
    pass


@bq.group()
def schema() -> None:
    pass


@schema.command()
@click.option(
    "-e",
    "--env",
    required=True,
    type=click.Choice(ENVIRONMENTS),
    help="Environments to which the migration applies (dev/prod)",
)
@click.option(
    "-p", "--project", required=True, type=str, help="Project for storing the migration history"
)
@click.option(
    "-d", "--dataset", required=True, type=str, help="Dataset for storing the migration history"
)
@click.option(
    "-t", "--table", required=True, type=str, help="Table for storing the migration history"
)
@click.option("--parent-project", type=str, help="Project to run the query")
def migrate(env: str, project: str, dataset: str, table: str, parent_project: str) -> None:
    schema_history = SchemaHistory(
        env=env,
        dir=BASE_DIR / "bigquery" / "migrations",
        parent_project=parent_project if parent_project else project,
        project=project,
        dataset=dataset,
        table=table,
    )
    schema_history.migrate()
