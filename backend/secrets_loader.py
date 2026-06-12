"""
Load runtime config from AWS Secrets Manager at startup.

Production stores all app env vars (DATABASE_URL / CONWO_DB_*, ANTHROPIC_API_KEY,
GOOGLE_CLIENT_ID, ALLOWED_ORIGINS, TRACE_USER_HASH_SALT, JIRA_*, etc.) in a single
Secrets Manager secret. On import (before backend.config reads anything), we fetch
that secret and populate os.environ, so the rest of the app — which reads
os.getenv(...) — needs no changes.

Activation is opt-in via env, so local dev (which uses .env) is unaffected:
  CONWO_SECRET_ID        e.g. "prod/conwo"        (unset → skip entirely)
  CONWO_SECRET_REGION    e.g. "ap-southeast-1"    (falls back to AWS_REGION, then ap-southeast-1)

The secret's value must be a JSON object of KEY: value pairs.

AWS auth: in EKS this comes from IRSA (the pod's service account → an IAM role
with secretsmanager:GetSecretValue on the secret). boto3 picks it up
automatically — no AWS keys in env.

Fail-loud: if CONWO_SECRET_ID is set but the fetch/parse fails, we raise — the
app cannot start without its DB credentials, so a silent skip would only produce
a confusing downstream error.
"""
from __future__ import annotations

import json
import logging
import os

_log = logging.getLogger("uvicorn.error")


def _apply_secret_json(raw: str) -> int:
    """Parse a Secrets Manager JSON blob and set each key into os.environ.
    Returns the number of keys applied. Pure/testable — no AWS."""
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(
            "Secrets Manager value must be a JSON object of KEY: value env vars"
        )
    for key, value in data.items():
        os.environ[str(key)] = "" if value is None else str(value)
    return len(data)


def load_aws_secrets() -> None:
    """Fetch CONWO_SECRET_ID from AWS Secrets Manager and load it into os.environ.
    No-op when CONWO_SECRET_ID is unset (local dev). Raises on failure when set."""
    secret_id = os.getenv("CONWO_SECRET_ID", "").strip()
    if not secret_id:
        return  # local dev / not using Secrets Manager

    region = (
        os.getenv("CONWO_SECRET_REGION")
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or "ap-southeast-1"
    ).strip()

    try:
        import boto3  # imported lazily so local dev doesn't need it installed

        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId=secret_id)
        raw = resp.get("SecretString")
        if not raw:
            raise RuntimeError(f"secret {secret_id!r} has no SecretString")
        count = _apply_secret_json(raw)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load config from AWS Secrets Manager "
            f"(id={secret_id!r}, region={region!r}): {exc}. "
            "Check CONWO_SECRET_ID/region and that the pod's IAM role has "
            "secretsmanager:GetSecretValue on that secret."
        ) from exc

    _log.info(
        "Loaded %d env vars from AWS Secrets Manager (id=%s, region=%s)",
        count, secret_id, region,
    )
