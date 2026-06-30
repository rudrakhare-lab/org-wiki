"""Download bge-reranker-v2-m3 weights to /app/models/. Run during Docker build.

Idempotent: if the target directory already exists with the expected files, skip.
"""
import os
import sys
from pathlib import Path

MODEL_ID = "BAAI/bge-reranker-v2-m3"
TARGET = Path(os.getenv("RERANKER_MODEL_DIR", "/app/models/bge-reranker-v2-m3"))

def main() -> int:
    if (TARGET / "config.json").exists() and (TARGET / "tokenizer.json").exists():
        print(f"reranker model already present at {TARGET}", flush=True)
        return 0
    TARGET.mkdir(parents=True, exist_ok=True)
    from sentence_transformers import CrossEncoder
    CrossEncoder(MODEL_ID).save(str(TARGET))
    print(f"reranker model downloaded to {TARGET}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
