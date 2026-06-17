import functools
from flask import Blueprint, render_template, redirect, url_for, request, session, flash, abort
from werkzeug.security import check_password_hash
from db_helper import execute_query, log_activity

auth_bp = Blueprint('auth', __name__)

def login_required(view):
    """
    Decorator that redirects user to login if they are not authenticated.
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

def roles_required(*allowed_roles):
    """
    Decorator that checks if the logged-in user belongs to any of the allowed roles.
    Must be used *after* @login_required.
    """
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            user_role = session.get('role_name')
            if user_role not in allowed_roles:
                log_activity(
                    session.get('user_id'), 
                    'Access Denied', 
                    f"Attempted to access {request.path} which requires roles: {', '.join(allowed_roles)}"
                )
                abort(403) # Forbidden
            return view(**kwargs)
        return wrapped_view
    return decorator

@auth_bp.route('/login', methods=('GET', 'POST'))
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('login.html')
            
        try:
            # Query user using parameterized query to avoid SQL Injection
            query = """
                SELECT u.id, u.username, u.password_hash, r.name as role_name, r.id as role_id 
                FROM users u 
                JOIN roles r ON u.role_id = r.id 
                WHERE u.username = %s
            """
            user_records = execute_query(query, (username,))
            
            if user_records and check_password_hash(user_records[0]['password_hash'], password):
                # Clear session to prevent session fixation attacks
                session.clear()
                
                # Store user info in Flask session
                session['user_id'] = user_records[0]['id']
                session['username'] = user_records[0]['username']
                session['role_name'] = user_records[0]['role_name']
                session['role_id'] = user_records[0]['role_id']
                
                # Log login event
                log_activity(session['user_id'], 'User Login', f"User {username} logged in successfully")
                
                flash(f"Welcome back, {username}!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
                
        except Exception as e:
            flash(f"Database error: {str(e)}", 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_activity(user_id, 'User Logout', f"User logged out")
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
