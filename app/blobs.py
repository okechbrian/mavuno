"""File storage abstraction — Vercel Blob in production, local filesystem in dev."""

from __future__ import annotations
import io
import os
import time
from pathlib import Path
from typing import Optional

from PIL import Image

from .config import ROOT

_BLOB_TOKEN = os.getenv("VERCEL_BLOB_READ_WRITE_TOKEN", "")
_USE_BLOB = bool(_BLOB_TOKEN)


def _process_webp_bytes(
    file_bytes: bytes, max_dim: int = 800, quality: int = 60
) -> bytes:
    """Resize and convert image bytes to compressed WebP."""
    img = Image.open(io.BytesIO(file_bytes))
    img.thumbnail((max_dim, max_dim))
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=quality, method=6)
    return out.getvalue()


def _blob_path(prefix: str, user_id: str, ext: str = "webp") -> str:
    return f"uploads/{prefix}/{prefix}_{user_id}_{int(time.time())}.{ext}"


async def upload_bytes(
    file_bytes: bytes,
    prefix: str,
    user_id: str,
    max_dim: int = 800,
    quality: int = 60,
) -> str:
    """Upload processed image bytes, returning a public URL.

    Uses Vercel Blob when VERCEL_BLOB_READ_WRITE_TOKEN is set, otherwise
    saves to the local static directory.
    """
    data = _process_webp_bytes(file_bytes, max_dim=max_dim, quality=quality)
    path = _blob_path(prefix, user_id)

    if _USE_BLOB:
        return await _upload_blob(path, data)
    return await _upload_local(path, data)


async def upload_file(
    file: "fastapi.UploadFile",  # noqa: F821
    prefix: str,
    user_id: str,
    max_dim: int = 800,
    quality: int = 60,
) -> str:
    """Upload an UploadFile (from FastAPI), returning a public URL."""
    content = await file.read()
    return await upload_bytes(
        content, prefix, user_id, max_dim=max_dim, quality=quality
    )


async def _upload_blob(path: str, data: bytes) -> str:
    from vercel_blob import put

    result = put(
        path,
        data,
        options={"access": "public", "addRandomSuffix": True},
    )
    return result.get("url", "")


async def _upload_local(path: str, data: bytes) -> str:
    fpath = ROOT / "app" / "static" / path
    fpath.parent.mkdir(parents=True, exist_ok=True)
    fpath.write_bytes(data)
    return f"/static/{path}"
