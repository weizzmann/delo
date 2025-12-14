"""Create initial Department and admin User.
Usage: set ADMIN_USERNAME and ADMIN_PASSWORD env vars or defaults will be used.
"""
import os
from app import create_app
from app.extensions import db
from app.models import Department, User


def create_admin(username='admin', password='adminpass', dept_name='Administration'):
    app = create_app()
    with app.app_context():
        dept = Department.query.filter_by(name=dept_name).first()
        if not dept:
            dept = Department(name=dept_name)
            db.session.add(dept)
            db.session.flush()
            print(f'Created department: {dept.name} (id={dept.id})')
        else:
            print(f'Department exists: {dept.name} (id={dept.id})')

        user = User.query.filter_by(username=username).first()
        if user:
            print(f'User exists: {user.username} (id={user.id})')
            user.set_password(password)
            db.session.commit()
            print(f'Updated password for {username}')
            return

        user = User(username=username, email=None, department_id=dept.id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f'Created admin user: {username} with password: {password}')


def create_departments_and_users():
    app = create_app()
    with app.app_context():
        # Create departments
        dept_a = Department.query.filter_by(name='Department A').first()
        if not dept_a:
            dept_a = Department(name='Department A')
            db.session.add(dept_a)
            db.session.flush()
            print(f'Created department: {dept_a.name} (id={dept_a.id})')

        dept_b = Department.query.filter_by(name='Department B').first()
        if not dept_b:
            dept_b = Department(name='Department B')
            db.session.add(dept_b)
            db.session.flush()
            print(f'Created department: {dept_b.name} (id={dept_b.id})')

        # Create users
        users = [
            ('user1', dept_a.id),
            ('user2', dept_a.id),
            ('user3', dept_b.id),
            ('user4', dept_b.id),
        ]

        for username, dept_id in users:
            user = User.query.filter_by(username=username, department_id=dept_id).first()
            if user:
                print(f'User exists: {user.username}')
                user.set_password('pass1')
                db.session.commit()
                print(f'Updated password for {username}')
                continue
            user = User(username=username, email=None, department_id=dept_id)
            user.set_password('pass1')
            db.session.add(user)
            print(f'Created user: {username} in department {dept_id}')

        db.session.commit()


if __name__ == '__main__':
    u = os.environ.get('ADMIN_USERNAME', 'admin')
    p = os.environ.get('ADMIN_PASSWORD', 'adminpass')
    d = os.environ.get('ADMIN_DEPARTMENT', 'Administration')
    create_admin(username=u, password=p, dept_name=d)
    create_departments_and_users()
