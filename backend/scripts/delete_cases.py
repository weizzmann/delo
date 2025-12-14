"""Delete all cases from the database."""
from app import create_app
from app.extensions import db
from app.models import Case

def delete_all_cases():
    app = create_app()
    with app.app_context():
        cases = Case.query.all()
        for case in cases:
            db.session.delete(case)
        db.session.commit()
        print(f'Deleted {len(cases)} cases')

if __name__ == '__main__':
    delete_all_cases()