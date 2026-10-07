import os
import sys
from pathlib import Path

import modal


# ============================================================
# Modal App
# ============================================================

app = modal.App("product-catalog-backend")


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# Whisper cache volume
# ============================================================

whisper_cache = modal.Volume.from_name(
    "product-catalog-whisper-cache",
    create_if_missing=True,
)


# ============================================================
# CPU Image
# ============================================================

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi",
        "uvicorn",
        "mysql-connector-python",
        "requests",
        "python-dotenv",
        "pydantic",
        "rapidfuzz",
        "pandas",
        "faster-whisper",
        "ctranslate2",
        "python-multipart",
    )
    .add_local_dir(
        PROJECT_ROOT / "backend",
        remote_path="/root/project/backend",
    )
    .add_local_dir(
        PROJECT_ROOT / "data",
        remote_path="/root/project/data",
    )
)


# ============================================================
# CPU Backend
# ============================================================

@app.function(
    image=image,
    cpu=2,
    memory=4096,
    timeout=1800,
    secrets=[
        modal.Secret.from_name("product-catalog-aiven")
    ],
    volumes={
        "/root/.cache/huggingface": whisper_cache,
    },
    env={
        "HF_HOME": "/root/.cache/huggingface",
        "XDG_CACHE_HOME": "/root/.cache",
        "MODAL_QWEN_URL": (
            "https://brainmagictechnova--product-catalog-qwen-generate.modal.run"
        ),
    },
)
@modal.asgi_app()
def fastapi_app():
    # Make project root available for backend imports
    sys.path.insert(0, "/root/project")

    # api.py uses relative paths such as:
    # data/product_images
    os.chdir("/root/project")

    from backend.api import app as fastapi_application

    return fastapi_application