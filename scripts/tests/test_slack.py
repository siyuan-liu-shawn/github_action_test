#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import textwrap
from unittest.mock import MagicMock, patch

import google
import pytest
from dataplatform_kubernetes.secretmanager import SecretManagerClient
from dataplatform_kubernetes.slack import get_gcp_secret, post_to_slack


@pytest.fixture
def mock_slack_web_client(mocker):
    return mocker.patch("dataplatform_kubernetes.slack.slack_sdk.WebClient", autospec=True)


def test_post_to_slack_success(mock_slack_web_client):
    mock_web_client_instance = MagicMock()
    mock_slack_web_client.return_value = mock_web_client_instance
    mock_web_client_instance.api_call.return_value = {"ok": True}

    message = "Test exception message"
    with patch("dataplatform_kubernetes.slack.get_gcp_secret", return_value="test-secret"):
        post_to_slack(
            project="test-project",
            env="test-env",
            username="BigQuery",
            icon_emoji=":bigquery:",
            title="Test",
            message=message,
            color="danger",
        )
    try:
        github_server = os.environ["GITHUB_SERVER_URL"]
        github_repo = os.environ["GITHUB_REPOSITORY"]
        github_action_run_id = os.environ["GITHUB_RUN_ID"]
    except KeyError:
        pass
    gha_url = f"{github_server}/{github_repo}/actions/runs/{github_action_run_id}"

    expected_attachment = [
        {
            "title": "Test",
            "color": "danger",
            "fields": [
                {"title": "env", "value": "test-env", "short": True},
                {"title": "project", "value": "test-project", "short": True},
                {"title": "url", "value": gha_url, "short": False},
            ],
            "text": textwrap.dedent(
                f"""
                ```
                {message}
                ```
                """
            ),
        }
    ]
    mock_web_client_instance.api_call.assert_called_once_with(
        "chat.postMessage",
        json={
            "username": "BigQuery",
            "icon_emoji": ":bigquery:",
            "text": "",
            "attachments": json.dumps(expected_attachment),
            "channel": "#mp-alert-datapf-dev",
        },
    )


def test_post_to_slack_failure(mock_slack_web_client, caplog):
    mock_web_client_instance = MagicMock()

    mock_slack_web_client.return_value = mock_web_client_instance
    mock_web_client_instance.api_call.return_value = {
        "ok": False,
        "error": "API call error",
    }

    with pytest.raises(
        RuntimeError, match="Failed to post message to Slack. Error: API call error"
    ):
        with patch("dataplatform_kubernetes.slack.get_gcp_secret", return_value="test-secret"):
            post_to_slack(
                project="test-project",
                env="test-env",
                username="BigQuery",
                icon_emoji=":bigquery:",
                title="Test",
                message="Test exception message",
                color="danger",
            )

    assert mock_web_client_instance.api_call.call_count == 1


def test_get_gcp_secret(mocker):
    mocker.patch(
        "dataplatform_kubernetes.secretmanager.SecretManagerServiceClient",
        mocker.Mock(spec=google.cloud.secretmanager.SecretManagerServiceClient),
    )
    mock_access_secret_version = mocker.patch.object(
        SecretManagerClient,
        "get_secret",
        return_value="secret",
    )
    actual = get_gcp_secret("projects/test-project/secrets/secret/versions/version")
    assert actual == "secret"
    mock_access_secret_version.assert_called_once_with(
        "projects/test-project/secrets/secret/versions/version"
    )
