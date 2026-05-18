from pathlib import Path
from fastapi import UploadFile


def ensure_parent_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


async def save_upload_file(upload_file: UploadFile, destination_path: str) -> str:
    ensure_parent_dir(destination_path)
    content = await upload_file.read()
    with open(destination_path, "wb") as f:
        f.write(content)
    return destination_path
