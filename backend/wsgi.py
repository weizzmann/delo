from app import create_app
from config import Config

# WSGI entrypoint для gunicorn/uwsgi
app = create_app(config_object=Config)
