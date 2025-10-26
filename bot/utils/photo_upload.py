"""Utilities for uploading photos to Cloudinary."""

from __future__ import annotations

import asyncio
import os
from io import IOBase
from typing import Optional

import cloudinary.uploader


async def upload_photo_to_cloudinary(
    file_obj: IOBase,
    *,
    public_id: Optional[str] = None,
    folder: Optional[str] = None,
) -> str:
    """Upload a file-like object to Cloudinary and return the secure URL."""

    if file_obj.seekable():
        file_obj.seek(0)

    upload_options: dict[str, str] = {}

    if public_id:
        upload_options["public_id"] = public_id

    target_folder = folder or os.getenv("CLOUDINARY_FOLDER")
    if target_folder:
        upload_options["folder"] = target_folder

    loop = asyncio.get_running_loop()

    def _upload() -> str:
        result = cloudinary.uploader.upload(file_obj, **upload_options)
        secure_url = result.get("secure_url") or result.get("url")
        if not secure_url:
            raise RuntimeError("Cloudinary upload did not return a URL")
        return secure_url

    return await loop.run_in_executor(None, _upload)

