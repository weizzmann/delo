from flask import render_template, redirect, url_for
from flask_login import login_required, logout_user
from . import main_bp


@main_bp.route('/')
@login_required
def index():
    return render_template('index.html')


@main_bp.route('/my-cases')
@login_required
def my_cases():
    return render_template('my_cases.html')


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
