import os
import random
import string
import secrets


def generate_token_str():
    return "".join(random.sample(string.ascii_letters + string.digits, 32))


def get_or_create_secret_key(filepath="config/secert.txt") -> str:
    if os.environ.get("SMARTTODO_SECRET_KEY"):
        value = os.environ["SMARTTODO_SECRET_KEY"]
        if len(value) < 32:
            raise RuntimeError("SMARTTODO_SECRET_KEY must contain at least 32 characters")
        return value
    if os.path.exists(filepath):
        with open(filepath) as f:
            return f.read().strip()
    else:
        secret = secrets.token_urlsafe(48)
        with open(filepath, "w") as f:
            f.write(secret)
        return secret
