#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler(sys.stdout))
LOGGER.setLevel(int(os.getenv("LOGGING_LEVEL", logging.INFO)))

BASE_DIR: Path = Path(__file__).parents[2]

ENVIRONMENT_DEV = "dev"
ENVIRONMENT_PROD = "prod"
ENVIRONMENTS = [
    ENVIRONMENT_DEV,
    ENVIRONMENT_PROD,
]

CLOUDSQL_KIND_MYSQL = "mysql"
CLOUDSQL_KIND_POSTGRESQL = "postgresql"
CLOUDSQL_KINDS = [
    CLOUDSQL_KIND_MYSQL,
    CLOUDSQL_KIND_POSTGRESQL,
]

CUE_COMMAND = "cue"
CUE_COMMAND_CMD = "cmd"
CUE_COMMAND_DUMP = "dump"
CUE_COMMAND_AVRO_AVDL = "avdl"
CUE_COMMAND_AVRO_AVSC = "avsc"
CUE_COMMAND_EVAL = "eval"
CUE_SCRIPTS_DIR = Path(__file__).parents[1]
CUE_CLI_TOOL_FILE = "cli_tool.cue"
CUE_AVRO_TOOL_FILE = "avro_tool.cue"
CUE_DELIVERY_FILE = "delivery.cue"
AVRO_AVDL_FILE = "*.avdl"


@dataclass
class ContextArgument:
    pass
