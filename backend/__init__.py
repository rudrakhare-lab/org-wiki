from backend.secrets_loader import load_aws_secrets
from dotenv import load_dotenv

# Prod: populate os.environ from AWS Secrets Manager when CONWO_SECRET_ID is set
# (must run before backend.config / backend.db read any env). No-op in local dev.
load_aws_secrets()
# Local dev: fill any remaining vars from .env. override=False → never clobbers
# values already provided by Secrets Manager.
load_dotenv()
