#!/usr/bin/env python
# -*- coding: utf-8 -*-
import google
import pytest
from dataplatform_kubernetes.secretmanager import SecretManagerClient


@pytest.fixture
def mock_client(mocker):
    mock_client = mocker.Mock(spec=google.cloud.secretmanager.SecretManagerServiceClient)
    mocker.patch(
        "dataplatform_kubernetes.secretmanager.SecretManagerServiceClient",
        mock_client,
    )
    return mock_client


class TestSecretManagerClient:
    def test_get_gcp_secret(self, mocker, mock_client):
        mock_res = mocker.Mock(autospc=True)
        mock_res.payload.data = "secret".encode("utf-8")
        mock_client.return_value.access_secret_version.return_value = mock_res

        client = SecretManagerClient()
        actual = client.get_secret("projects/test-project/secrets/secret/versions/version")
        assert actual == "secret"
        mock_client.return_value.access_secret_version.assert_called_once_with(
            name="projects/test-project/secrets/secret/versions/version"
        )
