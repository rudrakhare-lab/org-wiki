"""
Tests for backend.secrets_loader — AWS Secrets Manager → os.environ.
AWS is mocked; no real network/credentials needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend import secrets_loader as sl


def test_apply_secret_json_sets_env(monkeypatch):
    monkeypatch.delenv("FOO", raising=False)
    monkeypatch.delenv("NUM", raising=False)
    n = sl._apply_secret_json('{"FOO": "bar", "NUM": 5}')
    import os
    assert n == 2
    assert os.environ["FOO"] == "bar"
    assert os.environ["NUM"] == "5"  # coerced to str


def test_apply_secret_json_none_becomes_empty(monkeypatch):
    monkeypatch.delenv("MAYBE", raising=False)
    sl._apply_secret_json('{"MAYBE": null}')
    import os
    assert os.environ["MAYBE"] == ""


def test_apply_secret_json_rejects_non_object():
    with pytest.raises(ValueError):
        sl._apply_secret_json('["not", "an", "object"]')


def test_load_skips_when_secret_id_unset(monkeypatch):
    """Local dev: no CONWO_SECRET_ID → no-op, no boto3 needed, no exception."""
    monkeypatch.delenv("CONWO_SECRET_ID", raising=False)
    with patch("boto3.client") as mock_client:
        sl.load_aws_secrets()
        mock_client.assert_not_called()  # never touches AWS


def test_load_from_mocked_secretsmanager(monkeypatch):
    monkeypatch.setenv("CONWO_SECRET_ID", "prod/conwo")
    monkeypatch.setenv("CONWO_SECRET_REGION", "ap-southeast-1")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    fake = MagicMock()
    fake.get_secret_value.return_value = {
        "SecretString": '{"DATABASE_URL": "postgresql://u:p@h:5432/db", '
                        '"ALLOWED_ORIGINS": "https://conwo.moveinsync.com"}'
    }
    with patch("boto3.client", return_value=fake) as mock_client:
        sl.load_aws_secrets()
        mock_client.assert_called_once_with("secretsmanager", region_name="ap-southeast-1")
        fake.get_secret_value.assert_called_once_with(SecretId="prod/conwo")

    import os
    assert os.environ["DATABASE_URL"] == "postgresql://u:p@h:5432/db"
    assert os.environ["ALLOWED_ORIGINS"] == "https://conwo.moveinsync.com"


def test_load_raises_clearly_on_fetch_failure(monkeypatch):
    monkeypatch.setenv("CONWO_SECRET_ID", "prod/conwo")
    fake = MagicMock()
    fake.get_secret_value.side_effect = Exception("AccessDenied")
    with patch("boto3.client", return_value=fake):
        with pytest.raises(RuntimeError, match="AWS Secrets Manager"):
            sl.load_aws_secrets()
