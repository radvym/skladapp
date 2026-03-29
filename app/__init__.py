from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask

from .config import Config
from .db import close_db, ensure_database
from .routes import bp


def create_app() -> Flask:
    config = Config.from_env()

    app = Flask(
        __name__,
        template_folder=str(config.base_dir / "templates"),
        static_folder=str(config.base_dir / "static"),
    )
    app.config.from_mapping(config.as_dict())

    _configure_logging(app)
    _ensure_runtime_directories(config)

    ensure_database(app)
    app.teardown_appcontext(close_db)
    app.register_blueprint(bp)

    return app


def _ensure_runtime_directories(config: Config) -> None:
    for path in [
        config.media_root,
        config.originals_dir,
        config.derived_dir,
        config.data_dir,
        config.logs_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def _configure_logging(app: Flask) -> None:
    log_path = Path(app.config["LOG_PATH"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    if not app.logger.handlers:
        app.logger.addHandler(file_handler)
    else:
        for handler in app.logger.handlers:
            handler.setFormatter(formatter)

    app.logger.setLevel(logging.INFO)
