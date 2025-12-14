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
        
        # Проверяем существование новых колонок в таблице volumes
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        
        columns = [col['name'] for col in inspector.get_columns('volumes')]
        
        # Добавляем новые колонки если их нет
        with db.engine.connect() as conn:
            if 'is_verified' not in columns:
                conn.execute(text('ALTER TABLE volumes ADD is_verified BIT DEFAULT 0'))
                print('Added column: is_verified')
            
            if 'verified_at' not in columns:
                conn.execute(text('ALTER TABLE volumes ADD verified_at DATETIME'))
                print('Added column: verified_at')
            
            if 'verified_by' not in columns:
                conn.execute(text('ALTER TABLE volumes ADD verified_by INT FOREIGN KEY REFERENCES users(id)'))
                print('Added column: verified_by')
            
            conn.commit()


if __name__ == '__main__':
    init_db()