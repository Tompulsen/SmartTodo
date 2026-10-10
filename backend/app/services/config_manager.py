import json
import os
from collections.abc import Iterable
from os.path import exists, join

from app.tools.log import logger


class ConfigManager:
    __CONFIG_FOLDER = "config"

    def __init__(self):
        self.account_db = None
        config_file = join(ConfigManager.__CONFIG_FOLDER, "config.json")
        if not exists(config_file):
            config_file = join(ConfigManager.__CONFIG_FOLDER, "default.json")
            logger.warning("Load Default Config")

        with open(config_file) as f:
            self.config: dict = json.load(f)

    def try_login(self, username: str, password: str) -> bool:
        users = self.config["USER_INFO"]
        return username in users and users[username]["password"] == password

    def get_roles(self, username: str) -> list[str]:
        if self.account_db is not None:
            from app.models.account import Account
            account = self.account_db.get(Account, username) if username else None
            return (["ROLE_USER", "ROLE_ADMIN"] if account.is_admin else ["ROLE_USER"]) if account and account.active else []
        users: dict = self.config["USER_INFO"]
        if username in users:
            return users[username]["role"]
        else:
            return []

    def is_admin_user(self, username: str):
        return "ROLE_ADMIN" in self.get_roles(username)

    def get_users_msg_info(self):
        ans = []
        for username, user_config in self.config["USER_INFO"].items():
            email = user_config.get("email")
            qw_hook = user_config.get("qw_hook")
            ans.append((username, email, qw_hook))
        return ans

    def get_llm_info(self):
        info = self.config["LLM_INFO"]
        return info["BASE_URL"], info["API_KEY"], info["MODEL_NAME"]

    def get_tool_llm_info(self):
        info = self.config.get("LLM_TOOL_INFO")
        if info is None:
            logger.warning("配置文件不包含简单工具LLM服务配置, 自动降级使用主模型配置")
            info = self.config["LLM_INFO"]
        return info["BASE_URL"], info["API_KEY"], info["MODEL_NAME"]

    def get_all_users(self) -> Iterable[str]:
        if self.account_db is not None:
            from sqlalchemy import select
            from app.models.account import Account
            return list(self.account_db.scalars(select(Account.username).where(Account.active.is_(True))))
        users: dict = self.config["USER_INFO"]
        return users.keys()

    def is_production(self) -> bool:
        return os.environ.get("ENV") == "PROD"
