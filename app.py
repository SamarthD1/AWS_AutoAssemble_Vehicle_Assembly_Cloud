import io
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, abort
from flask_wtf.csrf import CSRFProtect

from config import Config
import db_helper as db
from auth import auth_bp, login_required, roles_required

app = Flask(__name__)
app.config.from_object(Config)

# Enable Global CSRF Protection
csrf = CSRFProtect(app)

# Register Authentication Blueprint
app.register_blueprint(auth_bp)

# Context processor for layout template variables
@app.context_processor
def inject_global_vars():
    # Injects current time and active navigation state
    now = datetime.now()
    return {
        'current_time': now.strftime("%Y-%m-%d %H:%M:%S"),
        'active_page': request.endpoint
    }

# Error Handler for 403 Forbidden
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('base.html', active_page=None), 403

# Helper to calculate total pagination pages
def get_total_pages(total_items, items_per_page):
    return max(1, (total_items + items_per_page - 1) // items_per_page)

# ================= DASHBOARD =================

@app.route('/')
@login_required
def dashboard():
    try:
        # 1. Gather high-level KPI stats
        total_vehicles = db.execute_query("SELECT COUNT(*) as count FROM vehicles")[0]['count']
        in_production = db.execute_query("SELECT COUNT(*) as count FROM vehicles WHERE status = 'In Progress'")[0]['count']
        completed = db.execute_query("SELECT COUNT(*) as count FROM vehicles WHERE status = 'Completed'")[0]['count']
        pending_orders = db.execute_query("SELECT COUNT(*) as count FROM production_orders WHERE status = 'Planned'")[0]['count']
        active_employees = db.execute_query("SELECT COUNT(*) as count FROM employees")[0]['count']
        delayed_orders = db.execute_query("SELECT COUNT(*) as count FROM production_orders WHERE status = 'Delayed'")[0]['count']

        # 2. Gather Status breakdown data (for doughnut chart)
        status_rows = db.execute_query("SELECT status, COUNT(*) as count FROM vehicles GROUP BY status")
        status_breakdown = {row['status']: row['count'] for row in status_rows}
        # Ensure all statuses exist in dict for graphing consistency
        for status in ['Planned', 'In Progress', 'Quality Check', 'Completed', 'Delayed']:
            if status not in status_breakdown:
                status_breakdown[status] = 0

        # 3. Monthly production performance for Completed vehicles (for bar chart)
        # Filters to completed vehicles this year
        current_year = datetime.now().year
        monthly_rows = db.execute_query(
            """
            SELECT DATE_FORMAT(completion_date, '%b') as month, COUNT(*) as count 
            FROM vehicles 
            WHERE status = 'Completed' AND YEAR(completion_date) = %s
            GROUP BY MONTH(completion_date), month
            ORDER BY MONTH(completion_date)
            """, (current_year,)
        )
        monthly_production = {row['month']: row['count'] for row in monthly_rows}
        
        # Ensure standard months have data if empty
        standard_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for m in standard_months:
            if m not in monthly_production:
                monthly_production[m] = 0

        # 4. Employee workload - active tasks per employee (for workload horizontal bar)
        workload_rows = db.execute_query(
            """
            SELECT e.name, COUNT(t.id) as count 
            FROM employees e 
            LEFT JOIN tasks t ON e.id = t.employee_id AND t.status != 'Completed'
            GROUP BY e.id, e.name
            """
        )
        employee_workload = {row['name']: row['count'] for row in workload_rows}

        stats = {
            'total_vehicles': total_vehicles,
            'in_production': in_production,
            'completed': completed,
            'pending_orders': pending_orders,
            'active_employees': active_employees,
            'delayed_orders': delayed_orders,
            'status_breakdown': status_breakdown,
            'monthly_production': monthly_production,
            'employee_workload': employee_workload
        }
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        flash(f"Dashboard error: {str(e)}", "danger")
        return render_template('dashboard.html', stats={
            'total_vehicles': 0, 'in_production': 0, 'completed': 0,
            'pending_orders': 0, 'active_employees': 0, 'delayed_orders': 0,
            'status_breakdown': {}, 'monthly_production': {}, 'employee_workload': {}
        })

# ================= VEHICLE MANAGEMENT =================

@app.route('/vehicles')
@login_required
def vehicles_list():
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page
    
    try:
        # Safe SQL injection protection utilizing parameter binding
        if search_query:
            count_query = """
                SELECT COUNT(*) as count FROM vehicles 
                WHERE model LIKE %s OR type LIKE %s OR assembly_line LIKE %s OR status LIKE %s
            """
            param = f"%{search_query}%"
            total_items = db.execute_query(count_query, (param, param, param, param))[0]['count']
            
            data_query = """
                SELECT id, model, type, assembly_line, status, start_date, completion_date 
                FROM vehicles 
                WHERE model LIKE %s OR type LIKE %s OR assembly_line LIKE %s OR status LIKE %s
                ORDER BY id DESC LIMIT %s OFFSET %s
            """
            vehicles = db.execute_query(data_query, (param, param, param, param, per_page, offset))
        else:
            total_items = db.execute_query("SELECT COUNT(*) as count FROM vehicles")[0]['count']
            
            data_query = """
                SELECT id, model, type, assembly_line, status, start_date, completion_date 
                FROM vehicles 
                ORDER BY id DESC LIMIT %s OFFSET %s
            """
            vehicles = db.execute_query(data_query, (per_page, offset))

        total_pages = get_total_pages(total_items, per_page)
        return render_template('vehicles.html', vehicles=vehicles, search_query=search_query, page=page, total_pages=total_pages)
    except Exception as e:
        flash(f"Database read error: {str(e)}", "danger")
        return render_template('vehicles.html', vehicles=[], search_query='', page=1, total_pages=1)

@app.route('/vehicles/add', methods=['POST'])
@login_required
@roles_required('Administrator', 'Production Manager')
def add_vehicle():
    model = request.form.get('model', '').strip()
    v_type = request.form.get('type', '').strip()
    assembly_line = request.form.get('assembly_line', '').strip()
    status = request.form.get('status', '').strip()
    start_date = request.form.get('start_date') or None
    completion_date = request.form.get('completion_date') or None
    
    if not model or not v_type or not assembly_line or not status:
        flash("All fields are required to add a vehicle.", "danger")
        return redirect(url_for('vehicles_list'))
        
    try:
        # Automate dates based on status defaults
        if status == 'Completed' and not completion_date:
            completion_date = datetime.now().strftime('%Y-%m-%d')
        if status in ['In Progress', 'Quality Check', 'Completed'] and not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')

        insert_query = """
            INSERT INTO vehicles (model, type, assembly_line, status, start_date, completion_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        vehicle_id = db.execute_update(insert_query, (model, v_type, assembly_line, status, start_date, completion_date), return_lastrowid=True)
        
        # Log vehicle creation
        db.log_activity(session['user_id'], 'Vehicle Creation', f"Registered vehicle: {model} (ID: {vehicle_id}) with status {status}")
        flash(f"Vehicle VEH-{vehicle_id:04d} ({model}) added successfully.", "success")
    except Exception as e:
        flash(f"Failed to add vehicle: {str(e)}", "danger")
        
    return redirect(url_for('vehicles_list'))

@app.route('/vehicles/edit', methods=['POST'])
@login_required
@roles_required('Administrator', 'Production Manager')
def edit_vehicle():
    vehicle_id = request.form.get('id')
    model = request.form.get('model', '').strip()
    v_type = request.form.get('type', '').strip()
    assembly_line = request.form.get('assembly_line', '').strip()
    status = request.form.get('status', '').strip()
    start_date = request.form.get('start_date') or None
    completion_date = request.form.get('completion_date') or None
    
    if not vehicle_id or not model or not v_type or not assembly_line or not status:
        flash("All fields are required to edit a vehicle.", "danger")
        return redirect(url_for('vehicles_list'))

    try:
        # Auto-adjust dates based on status transitions
        if status == 'Completed' and not completion_date:
            completion_date = datetime.now().strftime('%Y-%m-%d')
        elif status != 'Completed':
            completion_date = None # Reset completion date if no longer completed
            
        if status in ['In Progress', 'Quality Check', 'Completed'] and not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        elif status == 'Planned':
            start_date = None

        update_query = """
            UPDATE vehicles 
            SET model = %s, type = %s, assembly_line = %s, status = %s, start_date = %s, completion_date = %s
            WHERE id = %s
        """
        db.execute_update(update_query, (model, v_type, assembly_line, status, start_date, completion_date, vehicle_id))
        
        # Also auto-update any linked production order status & progress
        if status == 'Completed':
            db.execute_update("UPDATE production_orders SET status = %s, progress_percentage = 100, estimated_completion_date = %s WHERE vehicle_id = %s", ('Completed', completion_date, vehicle_id))
        else:
            db.execute_update("UPDATE production_orders SET status = %s WHERE vehicle_id = %s", (status, vehicle_id))
            
        db.log_activity(session['user_id'], 'Vehicle Updates', f"Updated vehicle ID: {vehicle_id} to status {status}")
        flash(f"Vehicle VEH-{int(vehicle_id):04d} updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update vehicle: {str(e)}", "danger")
        
    return redirect(url_for('vehicles_list'))

@app.route('/vehicles/delete/<int:vehicle_id>', methods=['POST'])
@login_required
@roles_required('Administrator', 'Production Manager')
def delete_vehicle(vehicle_id):
    try:
        db.execute_update("DELETE FROM vehicles WHERE id = %s", (vehicle_id,))
        db.log_activity(session['user_id'], 'Vehicle Updates', f"Deleted vehicle ID: {vehicle_id}")
        flash(f"Vehicle VEH-{vehicle_id:04d} and associated records deleted.", "success")
    except Exception as e:
        flash(f"Failed to delete vehicle: {str(e)}", "danger")
    return redirect(url_for('vehicles_list'))

# ================= PRODUCTION TRACKING =================

@app.route('/production')
@login_required
def production_list():
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page
    
    try:
        # Search queries join orders with vehicles
        if search_query:
            count_query = """
                SELECT COUNT(*) as count 
                FROM production_orders o
                JOIN vehicles v ON o.vehicle_id = v.id
                WHERE v.model LIKE %s OR o.status LIKE %s
            """
            param = f"%{search_query}%"
            total_items = db.execute_query(count_query, (param, param))[0]['count']
            
            data_query = """
                SELECT o.id, o.vehicle_id, v.model as vehicle_model, o.progress_percentage, o.start_date, o.estimated_completion_date, o.status 
                FROM production_orders o
                JOIN vehicles v ON o.vehicle_id = v.id
                WHERE v.model LIKE %s OR o.status LIKE %s
                ORDER BY o.id DESC LIMIT %s OFFSET %s
            """
            orders = db.execute_query(data_query, (param, param, per_page, offset))
        else:
            total_items = db.execute_query("SELECT COUNT(*) as count FROM production_orders")[0]['count']
            data_query = """
                SELECT o.id, o.vehicle_id, v.model as vehicle_model, o.progress_percentage, o.start_date, o.estimated_completion_date, o.status 
                FROM production_orders o
                JOIN vehicles v ON o.vehicle_id = v.id
                ORDER BY o.id DESC LIMIT %s OFFSET %s
            """
            orders = db.execute_query(data_query, (per_page, offset))

        total_pages = get_total_pages(total_items, per_page)

        # Get list of vehicles NOT currently assigned to a production order (for ADD order modal)
        available_vehicles = db.execute_query(
            """
            SELECT id, model, status FROM vehicles 
            WHERE id NOT IN (SELECT vehicle_id FROM production_orders)
            """
        )
        
        # Get list of ALL vehicles (for EDIT order modal dropdown option)
        all_vehicles_list = db.execute_query("SELECT id, model FROM vehicles ORDER BY model")

        return render_template(
            'production.html', 
            orders=orders, 
            available_vehicles=available_vehicles, 
            all_vehicles_list=all_vehicles_list, 
            search_query=search_query, 
            page=page, 
            total_pages=total_pages
        )
    except Exception as e:
        flash(f"Database read error: {str(e)}", "danger")
        return render_template('production.html', orders=[], available_vehicles=[], all_vehicles_list=[], search_query='', page=1, total_pages=1)

@app.route('/production/add', methods=['POST'])
@login_required
@roles_required('Administrator', 'Production Manager')
def add_production():
    vehicle_id = request.form.get('vehicle_id')
    progress = request.form.get('progress_percentage', 0, type=int)
    start_date = request.form.get('start_date') or None
    estimated_completion_date = request.form.get('estimated_completion_date') or None
    status = request.form.get('status', 'Planned')
    
    if not vehicle_id:
        flash("Assigning a vehicle is required.", "danger")
        return redirect(url_for('production_list'))

    try:
        # Auto-adjust dates based on status
        if status == 'Completed':
            progress = 100
            if not estimated_completion_date:
                estimated_completion_date = datetime.now().strftime('%Y-%m-%d')
        if status in ['In Progress', 'Quality Check', 'Completed'] and not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')

        insert_query = """
            INSERT INTO production_orders (vehicle_id, progress_percentage, start_date, estimated_completion_date, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        order_id = db.execute_update(insert_query, (vehicle_id, progress, start_date, estimated_completion_date, status), return_lastrowid=True)
        
        # Sync vehicle status to match production order status
        if status == 'Completed':
            db.execute_update("UPDATE vehicles SET status = %s, start_date = %s, completion_date = %s WHERE id = %s", ('Completed', start_date, estimated_completion_date, vehicle_id))
        else:
            db.execute_update("UPDATE vehicles SET status = %s, start_date = %s WHERE id = %s", (status, start_date, vehicle_id))

        db.log_activity(session['user_id'], 'Production Updates', f"Created production order ID: {order_id} for vehicle ID: {vehicle_id}")
        flash(f"Production Order ORD-{order_id:04d} created successfully.", "success")
    except Exception as e:
        flash(f"Failed to create order: {str(e)}", "danger")
        
    return redirect(url_for('production_list'))

@app.route('/production/edit', methods=['POST'])
@login_required
@roles_required('Administrator', 'Production Manager')
def edit_production():
    order_id = request.form.get('id')
    vehicle_id = request.form.get('vehicle_id')
    progress = request.form.get('progress_percentage', 0, type=int)
    start_date = request.form.get('start_date') or None
    estimated_completion_date = request.form.get('estimated_completion_date') or None
    status = request.form.get('status')
    
    if not order_id or not vehicle_id or not status:
        flash("Missing mandatory fields.", "danger")
        return redirect(url_for('production_list'))

    try:
        if status == 'Completed':
            progress = 100
            if not estimated_completion_date:
                estimated_completion_date = datetime.now().strftime('%Y-%m-%d')
        elif status != 'Completed' and progress == 100:
            progress = 90  # Force progress back from 100 if status changed back

        # Update production order
        update_query = """
            UPDATE production_orders 
            SET vehicle_id = %s, progress_percentage = %s, start_date = %s, estimated_completion_date = %s, status = %s
            WHERE id = %s
        """
        db.execute_update(update_query, (vehicle_id, progress, start_date, estimated_completion_date, status, order_id))
        
        # Sync corresponding vehicle status & dates
        if status == 'Completed':
            db.execute_update("UPDATE vehicles SET status = %s, start_date = %s, completion_date = %s WHERE id = %s", ('Completed', start_date, estimated_completion_date, vehicle_id))
        else:
            db.execute_update("UPDATE vehicles SET status = %s, start_date = %s, completion_date = NULL WHERE id = %s", (status, start_date, vehicle_id))

        db.log_activity(session['user_id'], 'Production Updates', f"Updated production order ID: {order_id} status to {status}")
        flash(f"Production Order ORD-{int(order_id):04d} updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update order: {str(e)}", "danger")
        
    return redirect(url_for('production_list'))

@app.route('/production/staff-update', methods=['POST'])
@login_required
def staff_update_production():
    order_id = request.form.get('id')
    progress = request.form.get('progress_percentage', 0, type=int)
    status = request.form.get('status')
    
    if not order_id or not status:
        flash("Required data missing.", "danger")
        return redirect(url_for('production_list'))

    try:
        if status == 'Completed':
            progress = 100
        elif status != 'Completed' and progress == 100:
            progress = 90

        # Retrieve order details to know the associated vehicle ID
        order = db.execute_query("SELECT vehicle_id, start_date FROM production_orders WHERE id = %s", (order_id,))
        if not order:
            flash("Production order not found.", "danger")
            return redirect(url_for('production_list'))
            
        vehicle_id = order[0]['vehicle_id']
        start_date = order[0]['start_date']

        # Update order progress and status
        db.execute_update(
            "UPDATE production_orders SET progress_percentage = %s, status = %s WHERE id = %s", 
            (progress, status, order_id)
        )
        
        # Sync status on vehicle
        if status == 'Completed':
            today = datetime.now().strftime('%Y-%m-%d')
            db.execute_update("UPDATE vehicles SET status = %s, completion_date = %s WHERE id = %s", ('Completed', today, vehicle_id))
            db.execute_update("UPDATE production_orders SET estimated_completion_date = %s WHERE id = %s", (today, order_id))
        else:
            db.execute_update("UPDATE vehicles SET status = %s, completion_date = NULL WHERE id = %s", (status, vehicle_id))

        db.log_activity(session['user_id'], 'Production Updates', f"Staff updated progress on Order ID {order_id} to {progress}% ({status})")
        flash(f"Order ORD-{int(order_id):04d} progress updated to {progress}%.", "success")
    except Exception as e:
        flash(f"Failed to update progress: {str(e)}", "danger")
        
    return redirect(url_for('production_list'))

@app.route('/production/delete/<int:order_id>', methods=['POST'])
@login_required
@roles_required('Administrator', 'Production Manager')
def delete_production(order_id):
    try:
        db.execute_update("DELETE FROM production_orders WHERE id = %s", (order_id,))
        db.log_activity(session['user_id'], 'Production Updates', f"Deleted production order ID: {order_id}")
        flash(f"Production Order ORD-{order_id:04d} deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete order: {str(e)}", "danger")
    return redirect(url_for('production_list'))

# ================= EMPLOYEE & TASK MANAGEMENT =================

@app.route('/employees')
@login_required
def employees_list():
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page
    
    try:
        # Join employees and tasks to gather active tasks
        if search_query:
            count_query = """
                SELECT COUNT(DISTINCT e.id) as count 
                FROM employees e
                LEFT JOIN tasks t ON e.id = t.employee_id
                WHERE e.name LIKE %s OR e.department LIKE %s OR t.description LIKE %s
            """
            param = f"%{search_query}%"
            total_items = db.execute_query(count_query, (param, param, param))[0]['count']
            
            data_query = """
                SELECT e.id, e.name, e.department, e.role, t.id as task_id, t.description as task_description, t.status as task_status
                FROM employees e
                LEFT JOIN tasks t ON e.id = t.employee_id
                WHERE e.name LIKE %s OR e.department LIKE %s OR t.description LIKE %s
                ORDER BY e.id DESC LIMIT %s OFFSET %s
            """
            employees = db.execute_query(data_query, (param, param, param, per_page, offset))
        else:
            total_items = db.execute_query("SELECT COUNT(*) as count FROM employees")[0]['count']
            
            data_query = """
                SELECT e.id, e.name, e.department, e.role, t.id as task_id, t.description as task_description, t.status as task_status
                FROM employees e
                LEFT JOIN tasks t ON e.id = t.employee_id
                ORDER BY e.id DESC LIMIT %s OFFSET %s
            """
            employees = db.execute_query(data_query, (per_page, offset))

        total_pages = get_total_pages(total_items, per_page)
        return render_template('employees.html', employees=employees, search_query=search_query, page=page, total_pages=total_pages)
    except Exception as e:
        flash(f"Database error: {str(e)}", "danger")
        return render_template('employees.html', employees=[], search_query='', page=1, total_pages=1)

@app.route('/employees/add', methods=['POST'])
@login_required
@roles_required('Administrator', 'Production Manager')
def add_employee():
    name = request.form.get('name', '').strip()
    department = request.form.get('department', '').strip()
    role = request.form.get('role', '').strip()
    task_description = request.form.get('task_description', '').strip()
    task_status = request.form.get('task_status', '').strip()

    if not name or not department or not role:
        flash("Name, Department, and Role are mandatory.", "danger")
        return redirect(url_for('employees_list'))

    try:
        # Insert employee
        emp_id = db.execute_update(
            "INSERT INTO employees (name, department, role) VALUES (%s, %s, %s)", 
            (name, department, role), 
            return_lastrowid=True
        )

        # Insert assigned task if specified
        if task_status:
            if not task_description:
                task_description = "General operational duties"
            db.execute_update(
                "INSERT INTO tasks (employee_id, description, status) VALUES (%s, %s, %s)", 
                (emp_id, task_description, task_status)
            )

        db.log_activity(session['user_id'], 'Employee Creation', f"Registered employee: {name} (ID: {emp_id}) in {department}")
        flash(f"Employee EMP-{emp_id:04d} ({name}) added successfully.", "success")
    except Exception as e:
        flash(f"Failed to add employee: {str(e)}", "danger")
        
    return redirect(url_for('employees_list'))

@app.route('/employees/edit', methods=['POST'])
@login_required
@roles_required('Administrator', 'Production Manager')
def edit_employee():
    emp_id = request.form.get('id')
    name = request.form.get('name', '').strip()
    department = request.form.get('department', '').strip()
    role = request.form.get('role', '').strip()
    task_id_raw = request.form.get('task_id', '').strip()
    try:
        task_id = int(task_id_raw) if task_id_raw and task_id_raw.lower() not in ('none', 'null', '') else None
    except ValueError:
        task_id = None
    task_description = request.form.get('task_description', '').strip()
    task_status = request.form.get('task_status', '').strip()

    if not emp_id or not name or not department or not role:
        flash("Name, Department, and Role are mandatory.", "danger")
        return redirect(url_for('employees_list'))

    try:
        # Update employee details
        db.execute_update(
            "UPDATE employees SET name = %s, department = %s, role = %s WHERE id = %s", 
            (name, department, role, emp_id)
        )

        # Handle task updating or insertion
        if not task_id:
            # Check if the employee already has a task in the database
            existing_task = db.execute_query("SELECT id FROM tasks WHERE employee_id = %s LIMIT 1", (emp_id,))
            if existing_task:
                task_id = existing_task[0]['id']

        if task_status in ('Pending', 'In Progress', 'Completed'):
            if not task_description:
                task_description = "General operational duties"

            if task_id:
                # Update existing task
                db.execute_update(
                    "UPDATE tasks SET description = %s, status = %s WHERE id = %s", 
                    (task_description, task_status, task_id)
                )
            else:
                # Create new task
                db.execute_update(
                    "INSERT INTO tasks (employee_id, description, status) VALUES (%s, %s, %s)", 
                    (emp_id, task_description, task_status)
                )
        else:
            # No task selected or task cleared
            if task_id:
                # Task cleared, delete task
                db.execute_update("DELETE FROM tasks WHERE id = %s", (task_id,))

        db.log_activity(session['user_id'], 'Employee Updates', f"Updated employee: {name} (ID: {emp_id})")
        flash(f"Employee EMP-{int(emp_id):04d} updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update employee: {str(e)}", "danger")
        
    return redirect(url_for('employees_list'))

@app.route('/employees/delete/<int:emp_id>', methods=['POST'])
@login_required
@roles_required('Administrator', 'Production Manager')
def delete_employee(emp_id):
    try:
        db.execute_update("DELETE FROM employees WHERE id = %s", (emp_id,))
        db.log_activity(session['user_id'], 'Employee Updates', f"Deleted employee ID: {emp_id}")
        flash(f"Employee EMP-{emp_id:04d} deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete employee: {str(e)}", "danger")
    return redirect(url_for('employees_list'))

# ================= REPORTS MODULE =================

@app.route('/reports')
@login_required
@roles_required('Administrator', 'Production Manager')
def reports_view():
    try:
        # 1. Vehicle Production Report Dataset
        # Group status metrics per vehicle type
        vehicle_summary = db.execute_query(
            """
            SELECT type, 
                   SUM(CASE WHEN status = 'Planned' THEN 1 ELSE 0 END) as planned,
                   SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as inprogress,
                   SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
                   COUNT(*) as total
            FROM vehicles 
            GROUP BY type
            """
        )

        # 2. Employee Performance Report Dataset
        # Active employees and task details
        employee_summary = db.execute_query(
            """
            SELECT e.name, e.department, t.description as task_description, t.status as task_status
            FROM employees e
            LEFT JOIN tasks t ON e.id = t.employee_id
            ORDER BY e.department, e.name
            """
        )

        # 3. Production Efficiency Report Dataset
        # Average progress percentage of non-completed orders per assembly line
        efficiency_summary = db.execute_query(
            """
            SELECT v.assembly_line, 
                   COUNT(o.id) as active_count,
                   IFNULL(AVG(o.progress_percentage), 0) as avg_progress
            FROM vehicles v
            JOIN production_orders o ON o.vehicle_id = v.id
            WHERE o.status != 'Completed'
            GROUP BY v.assembly_line
            """
        )

        # Log report generation activity
        db.log_activity(session['user_id'], 'Report Generation', "Generated management reports summary view")

        return render_template(
            'reports.html', 
            vehicle_summary=vehicle_summary, 
            employee_summary=employee_summary, 
            efficiency_summary=efficiency_summary
        )
    except Exception as e:
        flash(f"Failed to generate reports: {str(e)}", "danger")
        return render_template('reports.html', vehicle_summary=[], employee_summary=[], efficiency_summary=[])

@app.route('/reports/export/<report_type>')
@login_required
@roles_required('Administrator', 'Production Manager')
def export_report(report_type):
    try:
        si = io.StringIO()
        cw = csv.writer(si)
        
        filename = f"{report_type}_report_{datetime.now().strftime('%Y%m%d')}.csv"
        
        if report_type == 'vehicles':
            cw.writerow(['Vehicle ID', 'Model', 'Type', 'Assembly Line', 'Status', 'Start Date', 'Completion Date'])
            rows = db.execute_query("SELECT id, model, type, assembly_line, status, start_date, completion_date FROM vehicles")
            for r in rows:
                cw.writerow([f"VEH-{r['id']:04d}", r['model'], r['type'], r['assembly_line'], r['status'], r['start_date'] or '', r['completion_date'] or ''])
                
        elif report_type == 'employees':
            cw.writerow(['Employee ID', 'Name', 'Department', 'Role', 'Task Description', 'Task Status'])
            rows = db.execute_query(
                """
                SELECT e.id, e.name, e.department, e.role, t.description, t.status 
                FROM employees e 
                LEFT JOIN tasks t ON e.id = t.employee_id
                """
            )
            for r in rows:
                cw.writerow([f"EMP-{r['id']:04d}", r['name'], r['department'], r['role'], r['description'] or '', r['status'] or ''])
                
        elif report_type == 'efficiency':
            cw.writerow(['Assembly Line', 'Active Orders Count', 'Average Progress (%)'])
            rows = db.execute_query(
                """
                SELECT v.assembly_line, COUNT(o.id) as count, AVG(o.progress_percentage) as avg_prog 
                FROM vehicles v 
                JOIN production_orders o ON o.vehicle_id = v.id 
                WHERE o.status != 'Completed'
                GROUP BY v.assembly_line
                """
            )
            for r in rows:
                cw.writerow([r['assembly_line'], r['count'], f"{r['avg_prog']:.2f}" if r['avg_prog'] is not None else '0.00'])
        else:
            abort(404)
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename={filename}"
        output.headers["Content-type"] = "text/csv"
        
        db.log_activity(session['user_id'], 'Report Export', f"Exported {report_type} report to CSV")
        return output
    except Exception as e:
        flash(f"CSV Export failed: {str(e)}", "danger")
        return redirect(url_for('reports_view'))

# ================= ACTIVITY LOGS MODULE =================

@app.route('/logs')
@login_required
@roles_required('Administrator')
def activity_logs_view():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    try:
        total_items = db.execute_query("SELECT COUNT(*) as count FROM activity_logs")[0]['count']
        
        query = """
            SELECT l.id, l.action, l.details, l.timestamp, u.username 
            FROM activity_logs l
            LEFT JOIN users u ON l.user_id = u.id
            ORDER BY l.timestamp DESC 
            LIMIT %s OFFSET %s
        """
        logs = db.execute_query(query, (per_page, offset))
        total_pages = get_total_pages(total_items, per_page)
        
        return render_template('activity_logs.html', logs=logs, page=page, total_pages=total_pages)
    except Exception as e:
        flash(f"Database error: {str(e)}", "danger")
        return render_template('activity_logs.html', logs=[], page=1, total_pages=1)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
