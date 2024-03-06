#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Any

import click
from dataplatform_kubernetes import ContextArgument
from dataplatform_kubernetes.bq import bq
from dataplatform_kubernetes.cue import cue
from dataplatform_kubernetes.gh import github
from dataplatform_kubernetes.scaffold import scaffold

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
def cli(ctx: Any) -> None:
    ctx.obj = ContextArgument()


cli.add_command(github)
cli.add_command(cue)
cli.add_command(bq)
cli.add_command(scaffold)

if __name__ == "__main__":
    cli()
