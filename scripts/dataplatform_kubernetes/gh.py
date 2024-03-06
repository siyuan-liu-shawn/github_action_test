#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import textwrap
from typing import Iterable

import click
from dataplatform_kubernetes import ContextArgument
from github import Github
from github.Repository import Repository
from jinja2 import Template


@click.group
def github() -> None:
    pass


def _get_repo() -> Repository:
    g = Github(os.environ["GITHUB_TOKEN"])
    return g.get_repo(os.environ["GITHUB_REPOSITORY"])


@github.command()
@click.option("--env", type=str, required=True)
@click.option("--pr-number", type=int, required=True)
@click.option("--bucket", type=str, required=True)
@click.option("--branch", type=str, required=True)
@click.option("--exclude", type=str, required=True)
@click.argument("files", type=click.Path(exists=True, file_okay=True, resolve_path=True), nargs=-1)
@click.pass_obj
def create_dump_cue_comment(
    ctx: ContextArgument,
    env: str,
    pr_number: int,
    bucket: str,
    branch: str,
    exclude: str,
    files: Iterable[str],
) -> None:
    if not files:
        return
    cwd = os.getcwd()
    files = sorted([f.replace(cwd, "") for f in files])
    pattern = re.compile(exclude)
    upload_files = []
    for f in files:
        if not pattern.match(f):
            upload_files.append(f)

    if upload_files:
        header = Template(
            textwrap.dedent(
                """
                ## CUE dump result ({{ env }})
                Manifest files have been uploaded to GCS:
                """
            )
        ).render(env=env)
        body = Template(
            textwrap.dedent(
                """
                ```
                {% for f in files -%}
                {{ f }}
                {% endfor -%}
                ```
                """
            )
        ).render(files=[f"gs://{bucket}/{branch}{f}" for f in upload_files])

        repo = _get_repo()
        pull = repo.get_pull(pr_number)
        comments = pull.get_issue_comments()
        for c in comments:
            if c.user.login == "github-actions[bot]" and header in c.body:
                c.edit(header + "\n" + body)
                return
        pull.create_issue_comment(header + "\n" + body)
