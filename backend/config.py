# backend/config.py
import os

class Config:
    # минимум, дальше добавим MSSQL/SECRET_KEY и т.д.
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    JSON_SORT_KEYS = False
