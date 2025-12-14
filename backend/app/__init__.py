import os
from pathlib import Path

from flask import Flask, render_template, send_from_directory


def create_app(config_object) -> Flask:
    """
    config_object: класс/модуль конфига (например Config) или строка 'config.Config'
    """

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
        static_url_path="/static",
    )

    # Flask config: поддерживаем и объект, и строку (строка импортируется динамически)
    app.config.from_object(config_object)  # допускает object reference или import string [web:154]

    # --- API v1 ---
    # Минимальный api blueprint, чтобы проверить пайплайн.
    # Дальше подключим ваши реальные blueprints (auth/main/api) и начнем миграцию.
    try:
        from app.api_v1 import bp as api_v1_bp
        app.register_blueprint(api_v1_bp, url_prefix="/api/v1")
    except Exception:
        # чтобы приложение поднималось даже до добавления api_v1 пакета
        pass

    # --- SPA / Vue build inside Flask ---
    # Если Vue ещё не собран (index.html отсутствует), показываем заглушку.
    templates_dir = Path(app.template_folder or "templates")
    index_path = templates_dir / "index.html"

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def spa(path: str):
        # 1) API не перехватываем (пусть Flask сам 404/405 отдаёт)
        if path.startswith("api/"):
            return ("Not Found", 404)

        # 2) Если реально просят существующий файл из static (например assets),
        #    отдадим его (обычно Flask и сам отдаёт /static/*, но это полезно при прямых ссылках).
        if path.startswith("static/"):
            rel = path[len("static/") :]
            file_path = Path(app.static_folder) / rel
            if file_path.exists():
                return send_from_directory(app.static_folder, rel)

        # 3) Если сборка фронта ещё не сделана — покажем понятную страницу
        if not index_path.exists():
            return (
                "Frontend not built yet. Run: cd frontend && npm run build && then move dist into backend/app/templates+static.",
                503,
            )

        # 4) Всё остальное — SPA entrypoint
        return render_template("index.html")

    return app
