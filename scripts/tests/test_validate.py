#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
from dataplatform_kubernetes.validation import validate_project_id, validate_service_id


def test_validate_service_id():
    actual = validate_service_id(None, None, None)
    assert actual is None

    actual = validate_service_id(None, None, "foobar")
    assert actual == "foobar"

    actual = validate_service_id(None, None, "foo-bar")
    assert actual == "foo-bar"

    with pytest.raises(ValueError):
        validate_service_id(None, None, "foo_bar")


def test_validate_project_id():
    actual = validate_project_id(None, None, None)
    assert actual is None

    actual = validate_project_id(None, None, "foobar")
    assert actual == "foobar"

    actual = validate_project_id(None, None, "foo-bar")
    assert actual == "foo-bar"

    with pytest.raises(ValueError):
        validate_project_id(None, None, "foo_bar")
