from pathlib import Path
from flask import Blueprint, abort, request, send_from_directory
from sqlalchemy import select

from app import db, item_manager
from app.models.item import Item, ItemType
from app.tools.file import FILE_FOLDER
from app.views.authority import authority_check

file_bp = Blueprint('file', __name__)


@file_bp.post("/api/file/upload")
@authority_check()
def file_do_upload(owner: str):
    file = request.files['myFile']
    parent = int(request.form.get('parent', '0'))

    # 0表示不属于任何类型，转换为None类型进行存储
    if parent == 0:
        parent = None
    if parent is not None:
        item_manager.select_with_authority(parent, owner)

    item_manager.create_upload_file(file, parent, owner)
    return True


@file_bp.get("/file/<path:filename>")
@authority_check()
def file_download(filename, owner):
    item = db.scalar(select(Item).where(Item.owner == owner, Item.item_type == ItemType.File,
                                        Item.url == f"/file/{filename}"))
    if item is None:
        abort(404)
    return send_from_directory(Path(FILE_FOLDER).resolve(), filename, as_attachment=True,
                               download_name=item.name)
