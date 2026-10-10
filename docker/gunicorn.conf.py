import os

bind = os.environ.get("SMARTTODO_BIND", "0.0.0.0") + ":" + os.environ.get("PORT", "8080")
# The application's scheduler runs in process; keep exactly one worker.
workers = 1
worker_class = "gthread"
threads = 8
timeout = 120
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
capture_output = True
forwarded_allow_ips = "127.0.0.1"
