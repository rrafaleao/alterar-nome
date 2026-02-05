from flask import session, redirect, url_for
from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login_form'))
        return f(*args, **kwargs)
    return decorated_function


def store_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'store_id' not in session:
            return redirect(url_for('registration.show_registration_form'))
        return f(*args, **kwargs)
    return decorated_function