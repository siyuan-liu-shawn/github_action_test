#!/usr/bin/env python
# -*- coding: utf-8 -*-
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click
from dataplatform_kubernetes import (
    BASE_DIR,
    CLOUDSQL_KINDS,
    ENVIRONMENTS,
    ContextArgument,
)
from dataplatform_kubernetes.validation import validate_project_id, validate_service_id
from jinja2 import Environment, FileSystemLoader

RESOURCE_DIR = BASE_DIR / "scripts" / "resources" / "scaffold"
TEMPLATE_DIR = RESOURCE_DIR / "template"
TEMPLATE_ENV = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


@dataclass
class ScaffoldConfig:
    env: str
    service_id: str
    short_service_id: str

    def __post_init__(self):
        self.type = None
        self.template = None

    @property
    def project(self):
        return f"{self.service_id}-{self.env}"


@dataclass
class ScaffoldSpannerConfig(ScaffoldConfig):
    spanner_project: Optional[str]
    spanner_instance: str
    spanner_database: str
    slack_channel: str

    def __post_init__(self):
        self.type = "spanner"
        self.template = "dataflow_template.#SpannerToAvro.location"


@dataclass
class ScaffoldCloudSqlConfig(ScaffoldConfig):
    project_number: str
    cloudsql_kind: str
    cloudsql_region: str
    cloudsql_project: Optional[str]
    cloudsql_instance: str
    cloudsql_database: str
    slack_channel: str

    def __post_init__(self):
        self.type = "cloudsql"
        self.template = "dataflow_template.#JdbcToAvro.location"


@dataclass
class ScaffoldBeyondConfig(ScaffoldConfig):
    cloudsql_instance: str
    cloudsql_database: str
    slack_channel: str

    def __post_init__(self):
        self.type = "cloudsql"
        self.template = "dataflow_template.#JdbcToAvro.location"


@dataclass
class ScaffoldAccessLogConfig(ScaffoldConfig):
    def __post_init__(self):
        self.type = "access_log"


@dataclass
class ScaffoldEventLogConfig(ScaffoldConfig):
    log_name: str
    descriptor: str

    def __post_init__(self):
        self.type = "event_log"

    @property
    def table(self):
        return self.log_name.replace(".", "_").lower()


def _get_base_dir(config: ScaffoldConfig, mkdir=True) -> Path:
    base_dir = BASE_DIR / "manifests" / "microservices" / config.service_id
    if mkdir:
        base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def _get_env_dir(config: ScaffoldConfig, mkdir=True) -> Path:
    env_dir = BASE_DIR / "manifests" / "microservices" / config.service_id / config.env
    if mkdir:
        env_dir.mkdir(parents=True, exist_ok=True)
    return env_dir


def _generate_metadata_cue_files(config: ScaffoldConfig) -> None:
    base_dir = _get_base_dir(config)
    template_metadata = TEMPLATE_ENV.get_template("metadata.cue.jinja2")
    metadata_file = base_dir / "metadata.cue"
    if not metadata_file.exists():
        with open(metadata_file, "wt", encoding="utf-8") as f:
            f.write(template_metadata.render(config=config))
            f.write("\n")

    env_dir = _get_env_dir(config)
    template_metadata_env = TEMPLATE_ENV.get_template("env/metadata.cue.jinja2")
    metadata_env_file = env_dir / "metadata.cue"
    if not metadata_env_file.exists():
        with open(metadata_env_file, "wt", encoding="utf-8") as f:
            f.write(template_metadata_env.render(config=config))
            f.write("\n")

    if config.type == "spanner":
        template_database = TEMPLATE_ENV.get_template("env/spanner.cue.jinja2")
        database_file = env_dir / "spanner.cue"
        if not database_file.exists():
            with open(database_file, "wt", encoding="utf-8") as f:
                f.write(template_database.render(config=config))
                f.write("\n")
    elif config.type == "cloudsql":
        template_database = TEMPLATE_ENV.get_template("env/cloudsql.cue.jinja2")
        database_file = env_dir / "cloudsql.cue"
        if not database_file.exists():
            with open(database_file, "wt", encoding="utf-8") as f:
                f.write(template_database.render(config=config))
                f.write("\n")


def _generate_spanner_cue_files(config: ScaffoldSpannerConfig) -> None:
    env_dir = _get_env_dir(config)
    # common
    common_dir = env_dir / "argo-workflows" / "common"
    common_dir.mkdir(parents=True, exist_ok=True)
    for name, path in [
        ("common.cue", "common/common.cue.jinja2"),
        ("delivery.cue", "common/delivery.cue.jinja2"),
        ("semaphore.cue", "common/semaphore.cue.jinja2"),
    ]:
        template = TEMPLATE_ENV.get_template(path)
        with open((common_dir / name), "wt", encoding="utf-8") as f:
            f.write(template.render(config=config))
            f.write("\n")
    # query
    query_dir = (
        env_dir
        / "argo-workflows"
        / "spanner-to-bigquery"
        / config.spanner_instance
        / config.spanner_database
    )
    query_dir.mkdir(parents=True, exist_ok=True)
    for name, path in [
        ("delivery.cue", "spanner/delivery.cue.jinja2"),
        ("information_schema.cue", "spanner/information_schema.cue.jinja2"),
        ("parameter.cue", "spanner/parameter.cue.jinja2"),
        ("workflow_daily.cue", "spanner/workflow_daily.cue.jinja2"),
        ("workflow_hourly.cue", "spanner/workflow_hourly.cue.jinja2"),
    ]:
        template = TEMPLATE_ENV.get_template(path)
        with open((query_dir / name), "wt", encoding="utf-8") as f:
            f.write(template.render(config=config))
            f.write("\n")


def _generate_cloudsql_cue_files(config: ScaffoldCloudSqlConfig) -> None:
    env_dir = _get_env_dir(config)
    # common
    common_dir = env_dir / "argo-workflows" / "common"
    common_dir.mkdir(parents=True, exist_ok=True)
    for name, path in [
        ("common.cue", "common/common.cue.jinja2"),
        ("delivery.cue", "common/delivery.cue.jinja2"),
        ("semaphore.cue", "common/semaphore.cue.jinja2"),
    ]:
        template = TEMPLATE_ENV.get_template(path)
        with open((common_dir / name), "wt", encoding="utf-8") as f:
            f.write(template.render(config=config))
            f.write("\n")
    # query
    query_dir = (
        env_dir
        / "argo-workflows"
        / "cloudsql-to-bigquery"
        / config.cloudsql_instance
        / config.cloudsql_database
    )
    query_dir.mkdir(parents=True, exist_ok=True)
    for name, path in [
        ("delivery.cue", "cloudsql/delivery.cue.jinja2"),
        ("information_schema.cue", "cloudsql/information_schema.cue.jinja2"),
        ("parameter.cue", "cloudsql/parameter.cue.jinja2"),
        ("workflow_daily.cue", "cloudsql/workflow_daily.cue.jinja2"),
        ("workflow_hourly.cue", "cloudsql/workflow_hourly.cue.jinja2"),
    ]:
        template = TEMPLATE_ENV.get_template(path)
        with open((query_dir / name), "wt", encoding="utf-8") as f:
            f.write(template.render(config=config))
            f.write("\n")


def _generate_beyond_cue_files(config: ScaffoldBeyondConfig) -> None:
    env_dir = _get_env_dir(config)
    # metadata
    template_metadata_env = TEMPLATE_ENV.get_template("beyond/database.cue.jinja2")
    metadata_env_file = env_dir / f"{config.cloudsql_database}.cue"
    if not metadata_env_file.exists():
        with open(metadata_env_file, "wt", encoding="utf-8") as f:
            f.write(template_metadata_env.render(config=config))
            f.write("\n")
    # common
    common_dir = env_dir / "argo-workflows" / "common"
    common_dir.mkdir(parents=True, exist_ok=True)
    for name, path in [
        (f"{config.cloudsql_database}.cue", "beyond/common.cue.jinja2"),
    ]:
        template = TEMPLATE_ENV.get_template(path)
        with open((common_dir / name), "wt", encoding="utf-8") as f:
            f.write(template.render(config=config))
            f.write("\n")
    # database
    database_dir = env_dir / config.cloudsql_database
    database_dir.mkdir(parents=True, exist_ok=True)
    template_metadata_database = TEMPLATE_ENV.get_template("beyond/metadata.cue.jinja2")
    metadata_database_file = database_dir / "metadata.cue"
    if not metadata_database_file.exists():
        with open(metadata_database_file, "wt", encoding="utf-8") as f:
            f.write(template_metadata_database.render(config=config))
            f.write("\n")
    # query
    query_dir = (
        database_dir
        / "argo-workflows"
        / "cloudsql-to-bigquery"
        / config.cloudsql_instance
        / config.cloudsql_database
    )
    query_dir.mkdir(parents=True, exist_ok=True)
    for name, path in [
        ("delivery.cue", "beyond/delivery.cue.jinja2"),
        ("information_schema.cue", "beyond/information_schema.cue.jinja2"),
        ("parameter.cue", "beyond/parameter.cue.jinja2"),
        ("workflow_daily.cue", "beyond/workflow_daily.cue.jinja2"),
        ("workflow_hourly.cue", "beyond/workflow_hourly.cue.jinja2"),
    ]:
        template = TEMPLATE_ENV.get_template(path)
        with open((query_dir / name), "wt", encoding="utf-8") as f:
            f.write(template.render(config=config))
            f.write("\n")


def _generate_access_log_cue_files(config: ScaffoldAccessLogConfig) -> None:
    env_dir = _get_env_dir(config)
    output_dir = env_dir / "flink" / "access-log-to-bigquery"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, path in [
        ("access_log_to_bigquery.cue", "access_log/access_log_to_bigquery.cue.jinja2"),
        ("delivery.cue", "access_log/delivery.cue.jinja2"),
    ]:
        template = TEMPLATE_ENV.get_template(path)
        with open((output_dir / name), "wt", encoding="utf-8") as f:
            f.write(template.render(config=config))
            f.write("\n")


def _generate_event_log_cue_files(config: ScaffoldEventLogConfig) -> None:
    env_dir = _get_env_dir(config)
    output_dir = env_dir / "flink" / "event-log-to-bigquery"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, path in [
        ("event_log_to_bigquery.cue", "event_log/event_log_to_bigquery.cue.jinja2"),
        ("delivery.cue", "event_log/delivery.cue.jinja2"),
    ]:
        template = TEMPLATE_ENV.get_template(path)
        with open((output_dir / name), "wt", encoding="utf-8") as f:
            f.write(template.render(config=config))
            f.write("\n")


def _update_codeowners(service_id: str, team_id: str) -> None:
    codeowners = BASE_DIR / ".github" / "CODEOWNERS"
    append = textwrap.dedent(
        f"""
        /manifests/microservices/{service_id} @kouzoh/{team_id} @kouzoh/merpay-dataplatform-jp
        /pkg/microservices/{service_id} @kouzoh/{team_id} @kouzoh/merpay-dataplatform-jp
        """
    )
    owners = codeowners.read_text()
    with open(codeowners, "at", encoding="utf-8") as f:
        if append not in owners:
            f.write(append)


def _make_pkg_dir(service_id: str) -> None:
    pkg_dir = BASE_DIR / "pkg" / "microservices" / service_id
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / ".gitkeep").touch()


@click.group()
def scaffold() -> None:
    pass


@scaffold.command()
@click.option("--env", type=click.Choice(ENVIRONMENTS), required=True)
@click.option("--service-id", type=str, required=True, callback=validate_service_id)
@click.option("--short-service-id", type=str, required=True, callback=validate_service_id)
@click.option("--team-id", type=str, required=True, callback=validate_service_id)
@click.option("--spanner-project", type=str, callback=validate_project_id)
@click.option("--spanner-instance", type=str, required=True)
@click.option("--spanner-database", type=str, required=True)
@click.option("--slack-channel", type=str)
@click.pass_obj
def spanner(
    ctx: ContextArgument,
    env: str,
    service_id: str,
    short_service_id: str,
    team_id: str,
    spanner_project: Optional[str],
    spanner_instance: str,
    spanner_database: str,
    slack_channel: str,
) -> None:
    config = ScaffoldSpannerConfig(
        env,
        service_id,
        short_service_id,
        spanner_project,
        spanner_instance,
        spanner_database,
        slack_channel,
    )
    _generate_metadata_cue_files(config)
    _generate_spanner_cue_files(config)
    _update_codeowners(service_id, team_id)
    _make_pkg_dir(service_id)


@scaffold.command()
@click.option("--env", type=click.Choice(ENVIRONMENTS), required=True)
@click.option("--service-id", type=str, required=True, callback=validate_service_id)
@click.option("--short-service-id", type=str, required=True, callback=validate_service_id)
@click.option("--team-id", type=str, required=True, callback=validate_service_id)
@click.option("--project-number", type=str, required=True)
@click.option("--cloudsql-kind", type=click.Choice(CLOUDSQL_KINDS), required=True)
@click.option("--cloudsql-region", type=str, required=True)
@click.option("--cloudsql-project", type=str, callback=validate_project_id)
@click.option("--cloudsql-instance", type=str, required=True)
@click.option("--cloudsql-database", type=str, required=True)
@click.option("--slack-channel", type=str)
@click.pass_obj
def cloudsql(
    ctx: ContextArgument,
    env: str,
    service_id: str,
    short_service_id: str,
    team_id: str,
    project_number: str,
    cloudsql_kind: str,
    cloudsql_region: str,
    cloudsql_project: Optional[str],
    cloudsql_instance: str,
    cloudsql_database: str,
    slack_channel: str,
) -> None:
    config = ScaffoldCloudSqlConfig(
        env,
        service_id,
        short_service_id,
        project_number,
        cloudsql_kind,
        cloudsql_region,
        cloudsql_project,
        cloudsql_instance,
        cloudsql_database,
        slack_channel,
    )
    _generate_metadata_cue_files(config)
    _generate_cloudsql_cue_files(config)
    _update_codeowners(service_id, team_id)
    _make_pkg_dir(service_id)


@scaffold.command()
@click.option("--env", type=click.Choice(ENVIRONMENTS), required=True)
@click.option("--cloudsql-instance", type=str, required=True)
@click.option("--cloudsql-database", type=str, required=True)
@click.option("--slack-channel", type=str)
@click.pass_obj
def beyond(
    ctx: ContextArgument,
    env: str,
    cloudsql_instance: str,
    cloudsql_database: str,
    slack_channel: str,
) -> None:
    service_id = "souzoh-beyond-jp"
    short_service_id = "sz-byd-jp"
    team_id = "souzoh-beyond-jp"
    config = ScaffoldBeyondConfig(
        env,
        service_id,
        short_service_id,
        cloudsql_instance,
        cloudsql_database,
        slack_channel,
    )
    _generate_beyond_cue_files(config)
    _update_codeowners(service_id, team_id)
    _make_pkg_dir(service_id)


@scaffold.command("access-log")
@click.option("--env", type=click.Choice(ENVIRONMENTS))
@click.option("--service-id", type=str, required=True, callback=validate_service_id)
@click.option("--short-service-id", type=str, required=True, callback=validate_service_id)
@click.option("--team-id", type=str, required=True, callback=validate_service_id)
@click.pass_obj
def access_log(
    ctx: ContextArgument,
    env: str,
    service_id: str,
    short_service_id: str,
    team_id: str,
) -> None:
    config = ScaffoldAccessLogConfig(
        env,
        service_id,
        short_service_id,
    )
    _generate_metadata_cue_files(config)
    _generate_access_log_cue_files(config)
    _update_codeowners(service_id, team_id)
    _make_pkg_dir(service_id)


@scaffold.command("event-log")
@click.option("--env", type=click.Choice(ENVIRONMENTS))
@click.option("--service-id", type=str, required=True, callback=validate_service_id)
@click.option("--short-service-id", type=str, required=True, callback=validate_service_id)
@click.option("--team-id", type=str, required=True, callback=validate_service_id)
@click.option("--log-name", type=str, required=True)
@click.option("--descriptor", type=str, required=True)
@click.pass_obj
def event_log(
    ctx: ContextArgument,
    env: str,
    service_id: str,
    short_service_id: str,
    team_id: str,
    log_name: str,
    descriptor: str,
) -> None:
    config = ScaffoldEventLogConfig(
        env,
        service_id,
        short_service_id,
        log_name,
        descriptor,
    )
    _generate_metadata_cue_files(config)
    _generate_event_log_cue_files(config)
    _update_codeowners(service_id, team_id)
    _make_pkg_dir(service_id)
