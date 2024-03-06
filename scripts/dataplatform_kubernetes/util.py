#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

import click
from dataplatform_kubernetes import AVRO_AVDL_FILE, BASE_DIR, CUE_DELIVERY_FILE


def exec_command(
    cmd: str, cwd: Optional[str] = None, echo: bool = True, check_return_code: bool = True
) -> Tuple[List[str], int]:
    if echo:
        click.echo(cmd)
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=-1,
        env=os.environ,
        cwd=cwd,
    )
    lines = []
    with io.open(proc.stdout.fileno(), closefd=False) as stream:  # type: ignore
        for line in stream:
            if echo:
                click.echo(line.rstrip())
            lines.append(line)
    proc.wait()
    return_code = proc.returncode
    if check_return_code and return_code != 0:
        click.echo("".join(lines))
        raise RuntimeError(f"Return code: {return_code}.")
    return lines, return_code


def get_changed_dir(changed: Iterable[Path]) -> Set[Path]:
    changed_dir = set()
    for c in changed:
        relative = str(c.relative_to(BASE_DIR))
        if not relative.startswith("manifests") and not relative.startswith("./manifests"):
            continue
        if c.is_dir():
            changed_dir.add(c)
        else:
            changed_dir.add(c.parent)
    return changed_dir


def get_changed_cue_dir(changed: Set[Path]) -> Set[Path]:
    cue_dir = set()
    for i in changed:
        for j in i.rglob(CUE_DELIVERY_FILE):
            cue_dir.add(j.parent)
    return cue_dir


def get_changed_avro_files(changed: Set[Path]):
    avro_files = set()
    for i in changed:
        for j in i.rglob(AVRO_AVDL_FILE):
            avro_files.add(j)
    return avro_files
