import logging
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile

from src.settings import RUNTIME_DATA_DIR

router = APIRouter(prefix="/file", tags=["File"])


@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()

    file_id = str(uuid4()) + "." + file.filename.split(".")[-1]

    file_path = RUNTIME_DATA_DIR / file_id
    with open(file_path, "wb") as f:
        f.write(contents)

    return {"file_id": file_id}
