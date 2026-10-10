FROM node:24-alpine AS frontend
WORKDIR /build
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm run build

FROM python:3.12-slim
ARG VCS_REF=unknown
LABEL org.opencontainers.image.source="https://github.com/Tompulsen/SmartTodo" \
      org.opencontainers.image.title="SmartTodo" \
      org.opencontainers.image.revision="${VCS_REF}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    PORT=8080 \
    SMARTTODO_WEB_ROOT=/app/web \
    SMARTTODO_LOCAL_MODE=0
WORKDIR /app
COPY backend/requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-production.txt \
    && useradd --uid 10001 --create-home smarttodo \
    && mkdir -p /app/data /app/config \
    && chown -R smarttodo:smarttodo /app
COPY --chown=smarttodo:smarttodo backend/ ./
COPY --chown=smarttodo:smarttodo config/default.json /app/default-config.json
COPY --chown=smarttodo:smarttodo --from=frontend /build/dist/ /app/web/
COPY docker/entrypoint.sh /usr/local/bin/smarttodo-entrypoint
COPY docker/gunicorn.conf.py /app/gunicorn.conf.py
USER smarttodo
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/api/health',timeout=3)"
ENTRYPOINT ["sh", "/usr/local/bin/smarttodo-entrypoint"]
CMD ["gunicorn", "--config", "/app/gunicorn.conf.py", "wsgi:app"]

