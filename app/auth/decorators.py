from functools import wraps
from flask import abort
from flask_login import current_user


def department_required(department_id_arg='department_id'):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            dep_id = kwargs.get(department_id_arg) or getattr(current_user, 'department_id', None)
            if current_user.is_authenticated and current_user.department_id == dep_id:
                return f(*args, **kwargs)
            abort(403)

        return wrapped

    return decorator
