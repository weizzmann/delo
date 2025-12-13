from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_login import login_user, logout_user, current_user
from ..extensions import db, login_manager
from ..models import User

auth_bp = Blueprint('auth', __name__, template_folder='templates')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    print(f"Login attempt: username={username}, password={password}")
    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400

    user = User.query.filter_by(username=username).first()
    print(f"User found: {user}")
    if not user or not user.check_password(password):
        print("Invalid credentials")
        return jsonify({'error': 'invalid credentials'}), 401

    login_user(user)
    print(f"Logged in user: {user.username}")
    return jsonify({'message': 'ok'})


@auth_bp.route('/logout', methods=['GET'])
def logout():
    if current_user.is_authenticated:
        logout_user()
    return jsonify({'message': 'logged out'})
