"""Script to create required tables for the app (users, departments, cases, volumes, volume_documents).
Run once after configuring MSSQL_CONNECTION_STRING.
"""
from app import create_app
from app.extensions import db


app = create_app()


def init_db():
    with app.app_context():
        db.create_all()
        print('Tables created (if not exist).')


if __name__ == '__main__':
    init_db()
