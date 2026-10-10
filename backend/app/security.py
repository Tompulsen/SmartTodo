from datetime import timedelta
import os
import secrets

from flask import current_app, g, jsonify, request, session
from werkzeug.middleware.proxy_fix import ProxyFix

from app.models.account import Account


def current_account(db):
    if "account" not in g:
        account = db.get(Account, session.get("username")) if session.get("username") else None
        if not account or not account.active or session.get("auth_version") != account.session_version:
            account = None
        g.account = account
    return g.account


def configure_security(app, db):
    app.config.update(
        LOCAL_MODE=os.environ.get("SMARTTODO_LOCAL_MODE") == "1",
        REGISTRATION_ENABLED=os.environ.get("SMARTTODO_REGISTRATION", "1") == "1",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SMARTTODO_SECURE_COOKIE", "0") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    )
    if os.environ.get("SMARTTODO_TRUST_PROXY") == "1":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    @app.before_request
    def csrf_protection():
        if app.config["LOCAL_MODE"] or not request.path.startswith("/api/"):
            return
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return
        sent = request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf_token", "")
        if not sent or not expected or not secrets.compare_digest(sent, expected):
            return jsonify({"error": "页面验证已失效，请刷新后重试。", "code": "csrf"}), 403

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "提交内容过大。"}), 413
