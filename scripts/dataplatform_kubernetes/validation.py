#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from typing import Any, Optional


def validate_service_id(ctx: Any, param: Any, value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    match = re.match(r"^[a-z0-9][a-z0-9-.]+[a-z0-9]$", value)
    if match:
        return value
    else:
        raise ValueError("Invalid service id.")


def validate_project_id(ctx: Any, param: Any, value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    match = re.match(r"^[a-zA-Z0-9][a-zA-Z0-9-.]+[a-zA-Z0-9]$", value)
    if match:
        return value
    else:
        raise ValueError("Invalid service id.")
