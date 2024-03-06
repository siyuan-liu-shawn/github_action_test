#!/usr/bin/env python
# -*- coding: utf-8 -*-
import concurrent
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, List

import click
from dataplatform_kubernetes import (
    BASE_DIR,
    CUE_AVRO_TOOL_FILE,
    CUE_CLI_TOOL_FILE,
    CUE_COMMAND,
    CUE_COMMAND_AVRO_AVDL,
    CUE_COMMAND_AVRO_AVSC,
    CUE_COMMAND_CMD,
    CUE_COMMAND_DUMP,
    CUE_COMMAND_EVAL,
    CUE_SCRIPTS_DIR,
    LOGGER,
    ContextArgument,
)
from dataplatform_kubernetes.util import (
    exec_command,
    get_changed_avro_files,
    get_changed_cue_dir,
    get_changed_dir,
)


@click.group()
def cue() -> None:
    pass


def _get_parent_cue_file_dir(base_dir: str, dir: Path) -> List[Path]:
    dirs = []
    while True:
        if base_dir == str(dir.resolve()):
            break
        if list(dir.glob("*.cue")):
            dirs.append(dir.resolve())
        dir = dir.parent
    return dirs


def _dump(cmd: str, output: str) -> str:
    LOGGER.debug(f"command: {cmd}")
    lines, _ = exec_command(cmd, echo=False)
    output = Path(output)
    output.parent.resolve().mkdir(parents=True, exist_ok=True)
    LOGGER.debug(f"outoput: {output}")
    with open(output, "wt", encoding="utf-8") as f:
        f.write("".join(lines))
    return str(output)


def _gen_avro(idl_cmd: str, schema_cmd: str) -> str:
    LOGGER.debug(f"command: {idl_cmd}")
    exec_command(idl_cmd, echo=False)
    LOGGER.debug(f"command: {schema_cmd}")
    lines, _ = exec_command(schema_cmd, echo=False)
    output = "".join(lines).strip()
    LOGGER.debug(f"outoput: {output}")
    return output


def _build_dump_command(cue_file_dir: Path, debug: bool = False) -> str:
    dirs = _get_parent_cue_file_dir(str(BASE_DIR), cue_file_dir.parent)
    if debug:
        cmd = [
            CUE_COMMAND,
            CUE_COMMAND_EVAL,
            "-c",
        ]
    else:
        cmd = [
            CUE_COMMAND,
            CUE_COMMAND_CMD,
            CUE_COMMAND_DUMP,
        ]
    cmd.append(f"./{cue_file_dir.relative_to(str(BASE_DIR))}")
    cmd.extend([str(f"./{d.relative_to(str(BASE_DIR))}") for d in dirs])
    if not debug:
        cmd.append(f"./{CUE_SCRIPTS_DIR.relative_to(str(BASE_DIR))}/{CUE_CLI_TOOL_FILE}")
    return " ".join(cmd)


def _build_avro_avdl_command(idl_file: Path) -> str:
    dirs = _get_parent_cue_file_dir(str(BASE_DIR), idl_file.parent)
    cmd = [
        CUE_COMMAND,
        CUE_COMMAND_CMD,
        "-t",
        f"idl_file={idl_file.resolve()}",
        "-t",
        f"output_dir={idl_file.parent.resolve()}/",
        CUE_COMMAND_AVRO_AVDL,
    ]
    cmd.extend([str(f"./{d.relative_to(str(BASE_DIR))}") for d in dirs])
    cmd.append(f"./{CUE_SCRIPTS_DIR.relative_to(str(BASE_DIR))}/{CUE_AVRO_TOOL_FILE}")
    return " ".join(cmd)


def _build_avro_avsc_command(idl_file: Path) -> str:
    dirs = _get_parent_cue_file_dir(str(BASE_DIR), idl_file.parent)
    cmd = [
        CUE_COMMAND,
        CUE_COMMAND_CMD,
        "-t",
        f"schema_dir={idl_file.parent.resolve()}/",
        "-t",
        f"output_dir={idl_file.parent.resolve()}/",
        CUE_COMMAND_AVRO_AVSC,
    ]
    cmd.extend([str(f"./{d.relative_to(str(BASE_DIR))}") for d in dirs])
    cmd.append(f"./{CUE_SCRIPTS_DIR.relative_to(str(BASE_DIR))}/{CUE_AVRO_TOOL_FILE}")
    return " ".join(cmd)


def _read_changed_file(changed_file: Path) -> List[Path]:
    files = []
    with changed_file.open() as f:
        lines = f.read()
        for line in lines.strip().split(" "):
            file = Path(line.strip())
            files.append(file.resolve())
    return files


def _get_changed_dir_from_prefix(prefix: str) -> List[Path]:
    dirs = []
    prefix_dir = Path("/".join(prefix.split("/")[:-1]))
    pattern = prefix.split("/")[-1]
    for dir in prefix_dir.iterdir():
        if re.match(pattern, dir.name):
            dirs.append(dir.resolve())
    return dirs


@cue.command()
@click.option("--max-worker", type=int, required=False, default=10)
@click.option("--debug", is_flag=True, default=False)
@click.option(
    "--file",
    type=click.Path(exists=True, dir_okay=True, file_okay=True, resolve_path=True, path_type=Path),
    required=False,
)
@click.option(
    "--prefix",
    type=str,
    required=False,
)
@click.argument(
    "inputs",
    type=click.Path(exists=True, dir_okay=True, file_okay=True, resolve_path=True, path_type=Path),
    nargs=-1,
)
@click.pass_obj
def dump(
    ctx: ContextArgument, debug: bool, max_worker, file: Path, prefix: str, inputs: Iterable[Path]
) -> None:
    inputs = list(inputs)
    if file:
        inputs.extend(_read_changed_file(file))
    if prefix:
        inputs.extend(_get_changed_dir_from_prefix(prefix))

    changed_dir = get_changed_dir(inputs)
    cue_dir = get_changed_cue_dir(changed_dir)
    avro_files = get_changed_avro_files(changed_dir)

    outputs = []
    with ThreadPoolExecutor(max_workers=max_worker) as e:
        fs = []
        for a in avro_files:
            idl_cmd = _build_avro_avdl_command(a)
            schema_cmd = _build_avro_avsc_command(a)
            if debug:
                exec_command(idl_cmd, echo=True)
                exec_command(schema_cmd, echo=True)
            else:
                fs.append(e.submit(_gen_avro, idl_cmd, schema_cmd))

        for c in cue_dir:
            cmd = _build_dump_command(c, debug)
            if debug:
                exec_command(cmd, echo=True)
            else:
                output = str(c.resolve()) + ".yaml"
                fs.append(e.submit(_dump, cmd, output))

        for f in concurrent.futures.as_completed(fs):
            outputs.append(f.result())

    click.echo(f"cue_files={' '.join(outputs)}")
