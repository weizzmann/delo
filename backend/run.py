import os

from app import create_app
from config import Config


def main() -> None:
    # Можно переопределить класс конфига через строку, но по умолчанию используем Config
    # DELO_CONFIG поддержим позже (когда появятся разные конфиги Dev/Prod).
    app = create_app(config_object=Config)

    # Flask dev server: 5001 (как договорились)
    app.run(host="127.0.0.1", port=5001, debug=True)


if __name__ == "__main__":
    main()
