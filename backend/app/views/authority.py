import functools
import logging
from typing import Any

from flask import Response, abort, current_app, jsonify, session

from app.models.exception import UnauthorizedException
from app.tools.log import logger


class authority_check:
    def __init__(self, role='ROLE_USER') -> None:
        self.role = role

    def __call__(self, func) -> Any:
        @functools.wraps(func)
        def wrapped_function(*args, **kwargs):
            if current_app.config.get("LOCAL_MODE"):
                owner = session.get("username")
                role_list = session.get("role")
            else:
                from app import db
                from app.security import current_account
                account = current_account(db)
                owner = account.username if account else None
                role_list = (["ROLE_USER", "ROLE_ADMIN"] if account.is_admin else ["ROLE_USER"]) if account else []
            if owner is None:
                logging.warning(f"当前用户未登录, 无法请求 {func.__name__} 接口")
                abort(401)
            if role_list is None or self.role not in role_list:
                logger.warning(f"用户 {owner} 缺少 {self.role} 权限")
                abort(403)

            try:
                rsp = func(*args, **kwargs, owner=owner)
                if isinstance(rsp, Response):
                    return rsp
                else:
                    return jsonify(rsp)
            except UnauthorizedException as e:
                logger.warning(e)
                abort(403)

        return wrapped_function
