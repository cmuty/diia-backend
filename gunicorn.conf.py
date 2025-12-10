# Gunicorn configuration file for DiiaBackend
import multiprocessing

# Server socket
bind = "0.0.0.0:10000"
backlog = 2048

# Worker processes
workers = 1  # Для Render.com используем 1 worker
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Увеличиваем таймаут до 120 секунд для инициализации БД
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "diia-backend"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (если нужно)
keyfile = None
certfile = None

