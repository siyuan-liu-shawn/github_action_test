#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import textwrap
from typing import Optional

import slack_sdk
from dataplatform_kubernetes import LOGGER
from dataplatform_kubernetes.secretmanager import SecretManagerClient
from slack_sdk.errors import SlackApiError


def post_to_slack(
    project: str,
    env: str,
    title: str,
    color: str,
    message: str,
    icon_emoji: str,
    username: str,
    text: str = "",
) -> None:
    params = {
        "text": text,
        "username": username,
        "icon_emoji": icon_emoji,
        "attachments": format_message_attachment(
            project=project, env=env, title=title, color=color, message=message
        ),
    }
    if env == "prod":
        params.update({"channel": "#mp-alert-datapf"})
        secret_name = "projects/216572124863/secrets/slack-api-token/versions/latest"
    else:
        params.update({"channel": "#mp-alert-datapf-dev"})
        secret_name = "projects/518261476924/secrets/slack-api-token/versions/latest"
    client = slack_sdk.WebClient(token=get_gcp_secret(secret_name))
    try:
        LOGGER.info(params)
        response = client.api_call("chat.postMessage", json=params)
        if response["ok"]:
            LOGGER.info("Exception message posted to Slack successfully.")
        else:
            raise RuntimeError(f"Failed to post message to Slack. Error: {response['error']}")
    except SlackApiError as e:
        raise RuntimeError(f"Failed to post message to Slack. Error: {e.response['error']}")


def format_message_attachment(project: str, env: str, title: str, color: str, message: str) -> str:
    gha_url: Optional[str] = None
    try:
        github_server = os.environ["GITHUB_SERVER_URL"]
        github_repo = os.environ["GITHUB_REPOSITORY"]
        github_action_run_id = os.environ["GITHUB_RUN_ID"]
    except KeyError:
        pass
    gha_url = f"{github_server}/{github_repo}/actions/runs/{github_action_run_id}"
    fields = [
        {"title": "env", "value": env, "short": True},
        {"title": "project", "value": project, "short": True},
        {"title": "url", "value": gha_url, "short": False},
    ]
    attachment = [
        {
            "title": title,
            "color": color,
            "fields": fields,
            "text": textwrap.dedent(
                f"""
                ```
                {message}
                ```
                """
            ),
        }
    ]
    return json.dumps(attachment)


def get_gcp_secret(secret_name: str) -> str:
    client = SecretManagerClient()
    return client.get_secret(secret_name)
