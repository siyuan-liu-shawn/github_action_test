#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import contextlib
import hashlib
import re
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, List, Optional, cast

from dataplatform_kubernetes import LOGGER, slack
from google.cloud.bigquery import Client, SchemaField, Table, dbapi
from google.cloud.bigquery.job import QueryJobConfig

MIGRATION_FILE_PATTERN = re.compile(r"V(?P<version>[0-9]+)__(?P<description>.+)\.sql")


@dataclass
class SchemaMigrationConfig:
    script: str
    version: datetime
    description: str
    checksum: str
    queries: List[str]

    @staticmethod
    def calc_checksum(file: Path) -> str:
        md5 = hashlib.md5()
        with file.open("rb") as f:
            md5.update(f.read())
        return md5.hexdigest()

    @staticmethod
    def read(file: Path) -> SchemaMigrationConfig:
        match = MIGRATION_FILE_PATTERN.search(file.name)
        if match:
            version = datetime.strptime(match.group("version"), "%Y%m%d%H%M%S")
            description = match.group("description")
        else:
            raise RuntimeError("Illegal file name.")
        with file.open("r") as f:
            query = f.read()
        return SchemaMigrationConfig(
            file.name,
            version,
            description,
            SchemaMigrationConfig.calc_checksum(file),
            [q.strip() for q in query.split(";") if q.strip()],
        )

    @property
    def installed_on(self):
        return datetime.utcnow()


class SchemaHistory:
    def __init__(
        self, env: str, dir: Path, parent_project: str, project: str, dataset: str, table: str
    ):
        self.env = env
        self.dir = dir
        self.parent_project = parent_project
        self.project = project
        self.dataset = dataset
        self.table = table

        self._client = Client(project=self.parent_project)
        self._create_schema_history_table()

    @staticmethod
    def schema():
        return [
            SchemaField("installed_rank", "INTEGER", mode="NULLABLE"),
            SchemaField("version", "TIMESTAMP", mode="NULLABLE"),
            SchemaField("description", "STRING", mode="NULLABLE"),
            SchemaField("script", "STRING", mode="NULLABLE"),
            SchemaField("checksum", "STRING", mode="NULLABLE"),
            SchemaField("installed_on", "TIMESTAMP", mode="NULLABLE"),
            SchemaField("execution_time", "INTEGER", mode="NULLABLE"),
            SchemaField("success", "BOOLEAN", mode="NULLABLE"),
        ]

    @property
    def history_table(self):
        return f"{self.project}.{self.dataset}.{self.table}"

    @contextlib.contextmanager
    def dbapi_connection(self) -> Iterator[dbapi.Connection]:
        conn = dbapi.Connection(self._client)
        try:
            # TODO PermissionDenied: bigquery.readsessions.create
            conn._bqstorage_client = None
            conn._owns_bqstorage_client = False
            yield conn
        except Exception as e:
            LOGGER.error(f"Unexpected error occurred in DB-API connection: {repr(e)}.")
            raise e
        finally:
            conn.close()

    def read_migration_config(self) -> List[SchemaMigrationConfig]:
        migrations = []
        for g in (self.dir / self.env).glob("V[0-9]*__*.sql"):
            migrations.append(SchemaMigrationConfig.read(g))
        return sorted(migrations, key=lambda x: x.version)

    def _create_schema_history_table(self) -> None:
        schema = SchemaHistory.schema()
        table = Table(self.history_table, schema=schema)
        self._client.create_table(table, exists_ok=True)

    def _run_query(self, query: str, dryrun: bool = False) -> None:
        with self.dbapi_connection() as conn:
            cursor = conn.cursor()
            job_config = QueryJobConfig(use_legacy_sql=False, use_query_cache=False, dry_run=dryrun)
            LOGGER.info(f"Migrate :\n{query}")
            cursor.execute(query, job_config=job_config)

    def get_max_installed_rank(self) -> int:
        with self.dbapi_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT MAX(installed_rank) AS installed_rank FROM `{self.history_table}`
                """
            )
            result = cursor.fetchall()
            installed_rank = cast(int, result[0].installed_rank)
            if not installed_rank:
                return 1
            else:
                return installed_rank + 1

    def get_schema_history(self, version: datetime) -> Any:
        with self.dbapi_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT * FROM `{self.history_table}`
                WHERE version = %s
                """,
                (version.strftime("%Y-%m-%d %H:%M:%S"),),
            )
            return cursor.fetchall()

    def insert_schema_history(
        self,
        installed_rank: int,
        migration: SchemaMigrationConfig,
        execution_time: int,
        success: bool,
    ) -> Any:
        with self.dbapi_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                INSERT INTO `{self.history_table}`
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    installed_rank,
                    migration.version.strftime("%Y-%m-%d %H:%M:%S"),
                    migration.description,
                    migration.script,
                    migration.checksum,
                    migration.installed_on.strftime("%Y-%m-%d %H:%M:%S"),
                    execution_time,
                    success,
                ),
            )
            return cursor.fetchall()

    def _migrate(self, migration: SchemaMigrationConfig, dryrun: bool = False) -> Optional[str]:
        history = self.get_schema_history(migration.version)
        if history:
            if migration.checksum != history[0].checksum:
                slack.post_to_slack(
                    project=self.project,
                    env=self.env,
                    username="BigQuery",
                    icon_emoji=":bigquery:",
                    title="BigQuery schema migration failed",
                    message=f"Migration script checksum mismatch: {migration.script}",
                    color="danger",
                )
            LOGGER.info(f"Migration script has been applied: {migration.script}")
            return None

        installed_rank = self.get_max_installed_rank()
        start = time.time()
        exceptions = []
        try:
            for q in migration.queries:
                self._run_query(q, dryrun)
        except Exception:
            LOGGER.error(f"Schema migration failed: {migration.script}")
            exceptions.append(traceback.format_exc())
        elapsed = int((time.time() - start) * 1000)
        self.insert_schema_history(
            installed_rank, migration, elapsed, False if exceptions else True
        )
        if exceptions:
            exception = "\n\n".join(exceptions)
            slack.post_to_slack(
                project=self.project,
                env=self.env,
                username="BigQuery",
                icon_emoji=":bigquery:",
                title="BigQuery schema migration failed",
                message=f"Schema migration failed for: {migration.script} "
                f"and exception:\n\n{exception}",
                color="danger",
            )
            return None
        return migration.script

    def migrate(self):
        migrations = self.read_migration_config()
        executed_scripts = []
        for m in migrations:
            executed = self._migrate(m)
            if executed:
                executed_scripts.append(executed)

        if executed_scripts:
            message = "\n".join(executed_scripts)
            slack.post_to_slack(
                project=self.project,
                env=self.env,
                username="BigQuery",
                icon_emoji=":bigquery:",
                title="BigQuery schema migration was successful",
                message=f"Schema migration script execution completed successfully.\n{message}",
                color="good",
            )
