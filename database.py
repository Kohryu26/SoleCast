import sqlite3
import bcrypt
import pandas as pd
from datetime import datetime

DATABASE_FILE = 'solecast.db'

# --- Database Initialization ---

def init_db():
    """Initializes the database and creates all necessary tables."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    print("Initializing database...")

    # --- Table Creation (SCHEMA UPDATED TO MATCH ERD) ---
    
    # users (D.Storage 'Accounts Storage')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('Admin', 'Employee'))
    )
    ''')
    
    # materials (D.Storage 'Material Info Storage')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS materials (
        material_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        stock INTEGER NOT NULL,
        price REAL NOT NULL,
        product_association TEXT NOT NULL,
        unit_of_measure TEXT NOT NULL DEFAULT 'pcs'
    )
    ''')
    
    # sales_history (D.Storage 'Historical Data Storage')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sales_history (
        sales_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        is_historical_csv INTEGER NOT NULL DEFAULT 0
    )
    ''')
    
    # production_targets (D.Storage 'Quota Database')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS production_targets (
        target_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        target_quantity REAL NOT NULL,
        quota REAL NOT NULL,
        UNIQUE(product_name, year, month)
    )
    ''')
    
    # predictions (D.Storage 'Predictions Storage')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        predicted_quantity INTEGER NOT NULL
    )
    ''')
    
    # bom (Bill of Materials, Process 8)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bom (
        bom_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL, -- Storing product_name as per ERD attributes
        material_id INTEGER NOT NULL,
        quantity_per_unit INTEGER NOT NULL,
        FOREIGN KEY(material_id) REFERENCES materials(material_id) ON DELETE RESTRICT,
        UNIQUE(product_id, material_id)
    )
    ''')
    
    # --- Material Request Flow Tables (NEW) ---
    
    # Main request header, seen by Admin
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS material_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        employee_name TEXT NOT NULL,
        product_name TEXT NOT NULL,
        production_quantity INTEGER NOT NULL,
        total_cost REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        request_date TEXT NOT NULL,
        FOREIGN KEY(employee_id) REFERENCES users(user_id)
    )
    ''')
    
    # Line items for each request, seen by Admin
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS request_line_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        material_name TEXT NOT NULL,
        quantity_needed INTEGER NOT NULL,
        unit_of_measure TEXT NOT NULL DEFAULT 'pcs',
        cost REAL NOT NULL,
        FOREIGN KEY(request_id) REFERENCES material_requests(request_id) ON DELETE CASCADE
    )
    ''')
    
    # Local log for Employee's completed (but not submitted) orders
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS completed_material_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        employee_name TEXT NOT NULL,
        product_name TEXT NOT NULL,
        production_quantity INTEGER NOT NULL,
        total_cost REAL NOT NULL,
        completion_date TEXT NOT NULL,
        FOREIGN KEY(employee_id) REFERENCES users(user_id)
    )
    ''')
    
    # Line items for the local completed log
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS completed_order_line_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        material_name TEXT NOT NULL,
        quantity_needed INTEGER NOT NULL,
        cost REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES completed_material_orders(order_id) ON DELETE CASCADE
    )
    ''')
    
    conn.commit()
    print("Tables created successfully.")
    
    # --- Create Default Users ---
    # We must do this so the admin can log in the first time.
    try:
        create_user('admin', 'admin123', 'Admin', cursor, conn)
        print("User 'admin' created.")
    except sqlite3.IntegrityError:
        print("User 'admin' already exists.")
        
    try:
        create_user('employee', 'emp123', 'Employee', cursor, conn)
        print("User 'employee' created.")
    except sqlite3.IntegrityError:
        print("User 'employee' already exists.")

    conn.close()
    print("Database initialization complete.")

# --- User Management (Process 1 & 2) ---

def hash_password(password):
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def create_user(username, password, role, cursor, conn):
    """Inserts a new user with a hashed password."""
    hashed = hash_password(password)
    cursor.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, hashed, role)
    )
    conn.commit()

def add_new_user(username, password, role):
    """Adds a new user from the admin dashboard."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        create_user(username, password, role, cursor, conn)
    except Exception as e:
        conn.close()
        raise e
    conn.close()

def get_user(username):
    """Fetches a user's data by username for login verification."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # Return results as dictionaries
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_all_users():
    """Fetches all users for the admin 'Manage Accounts' tab."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, role FROM users") # <-- UPDATED
    users = cursor.fetchall()
    conn.close()
    return [dict(row) for row in users]

def update_user_role(user_id, new_role):
    """Updates a user's role."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, user_id)) # <-- UPDATED
    conn.commit()
    conn.close()
    
def update_user_password(username, new_password):
    """Updates a user's password (used for 'Forgot Password')."""
    hashed = hash_password(new_password)
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hashed, username))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """Deletes a user from the database."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,)) # <-- UPDATED
    conn.commit()
    conn.close()

# --- Material Management (Process 3) ---

def add_material(name, stock, price, assoc, unit):
    """Adds a new material to the inventory."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO materials (name, stock, price, product_association, unit_of_measure) VALUES (?, ?, ?, ?, ?)",
        (name, stock, price, assoc, unit)
    )
    conn.commit()
    conn.close()

def update_material(mat_id, name, stock, price, assoc, unit):
    """Updates an existing material's details."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE materials SET name = ?, stock = ?, price = ?, product_association = ?, unit_of_measure = ? WHERE material_id = ?", # <-- UPDATED
        (name, stock, price, assoc, unit, mat_id)
    )
    conn.commit()
    conn.close()

def delete_material(mat_id):
    """Deletes a material from the inventory."""
    conn = sqlite3.connect(DATABASE_FILE)
    # Enable foreign key enforcement to prevent deleting used items
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM materials WHERE material_id = ?", (mat_id,)) # <-- UPDATED
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise e # Re-raise the error to be caught by the UI
    conn.close()

def get_all_materials():
    """Fetches all materials for the 'Manage Materials' tab."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materials ORDER BY name")
    materials = cursor.fetchall()
    conn.close()
    return [dict(row) for row in materials]

def upsert_material_from_csv(name, stock, price, assoc, unit):
    """Adds a new material or updates an existing one from a CSV import."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO materials (name, stock, price, product_association, unit_of_measure)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            stock = excluded.stock,
            price = excluded.price,
            product_association = excluded.product_association,
            unit_of_measure = excluded.unit_of_measure
        """,
        (name, stock, price, assoc, unit)
    )
    conn.commit()
    conn.close()
    
# --- Sales & Target Management (Process 4, 7) ---

def add_sales_entry(product_name, year, month, quantity):
    """Adds a new (current) sales entry. is_historical_csv=0."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sales_history (product_name, year, month, quantity, is_historical_csv) VALUES (?, ?, ?, ?, 0)",
        (product_name, year, month, quantity)
    )
    conn.commit()
    conn.close()

def get_sales_history(is_historical_csv=None):
    """
    Fetches sales history.
    - is_historical_csv=True: Gets only 'Past Year' (CSV) data.
    - is_historical_csv=False: Gets only 'Current Year' (manual) data.
    - is_historical_csv=None: Gets all sales data.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    query = "SELECT * FROM sales_history"
    params = []
    
    if is_historical_csv is True:
        query += " WHERE is_historical_csv = 1"
    elif is_historical_csv is False:
        query += " WHERE is_historical_csv = 0"
        
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def save_production_target(product_name, year, month, target_quantity, target_increase):
    """Saves or updates a production target."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO production_targets (product_name, year, month, target_quantity, quota)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(product_name, year, month) DO UPDATE SET
            target_quantity = excluded.target_quantity,
            quota = excluded.quota
        """,
        (product_name, year, month, target_quantity, target_increase)
    )
    conn.commit()
    conn.close()

def get_production_targets():
    """Fetches all production targets."""
    conn = sqlite3.connect(DATABASE_FILE)
    df = pd.read_sql_query("SELECT * FROM production_targets", conn)
    conn.close()
    return df

def upsert_target_from_csv(product_name, year, month, target_quantity, target_increase):
    """Saves or updates a target from a CSV import."""
    save_production_target(product_name, year, month, target_quantity, target_increase)
    
# --- Forecasting (Process 5) ---

def clear_predictions():
    """Deletes all rows from the predictions table."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM predictions")
    conn.commit()
    conn.close()
    
def save_prediction(product_name, year, month, quantity):
    """Saves a single predicted data point."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO predictions (product_name, year, month, predicted_quantity) VALUES (?, ?, ?, ?)",
        (product_name, year, month, quantity)
    )
    conn.commit()
    conn.close()
    
def get_predictions():
    """Fetches all predictions."""
    conn = sqlite3.connect(DATABASE_FILE)
    df = pd.read_sql_query("SELECT * FROM predictions", conn)
    conn.close()
    return df

# --- Bill of Materials (BOM) (Process 8) ---

def add_bom_item(product_name, material_name, quantity):
    """
    Adds or updates an item in the BOM.
    Note: This is a simplified BOM that uses names instead of IDs
    for easier integration with other tables.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # We use a simplified text-based product_id for this system
    # and get the real material_id
    try:
        cursor.execute("SELECT material_id FROM materials WHERE name = ?", (material_name,)) # <-- UPDATED
        result = cursor.fetchone()
        if not result:
            raise Exception(f"Material not found: {material_name}")
        material_id = result[0]
        
        # Use product_name as the product_id for simplicity
        product_id_text = product_name
        
        cursor.execute(
            """
            INSERT INTO bom (product_id, material_id, quantity_per_unit)
            VALUES (?, ?, ?)
            ON CONFLICT(product_id, material_id) DO UPDATE SET
                quantity_per_unit = excluded.quantity_per_unit
            """,
            (product_id_text, material_id, quantity)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_full_bom():
    """
    Fetches the full BOM, joining with the materials table
    to get material names and units.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            b.bom_id, 
            b.product_id as product_name,
            m.name as material_name,
            b.quantity_per_unit,
            m.unit_of_measure
        FROM bom b
        JOIN materials m ON b.material_id = m.material_id
        ORDER BY product_name, material_name
        """ # <-- UPDATED
    )
    bom_items = cursor.fetchall()
    conn.close()
    return [dict(row) for row in bom_items]

def delete_bom_item(bom_item_id):
    """Deletes an item from the BOM by its ID."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bom WHERE bom_id = ?", (bom_item_id,)) # <-- UPDATED
    conn.commit()
    conn.close()

def get_bom_for_product(product_name):
    """
    Fetches all BOM items for a specific product,
    joining with materials to get stock, price, and unit info.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            m.name,
            b.quantity_per_unit,
            m.stock,
            m.price,
            m.unit_of_measure
        FROM bom b
        JOIN materials m ON b.material_id = m.material_id
        WHERE b.product_id = ?
        """, # <-- UPDATED
        (product_name,)
    )
    bom_items = cursor.fetchall()
    conn.close()
    return [dict(row) for row in bom_items]

# --- Material Request Functions (Employee & Admin) ---

def submit_material_request(employee_id, employee_name, product_name, production_quantity, total_cost, line_items):
    """Saves a new material request to the database for admin approval."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        # 1. Insert the main request
        request_date = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO material_requests 
            (employee_id, employee_name, product_name, production_quantity, total_cost, status, request_date)
            VALUES (?, ?, ?, ?, ?, 'Pending', ?)
            """,
            (employee_id, employee_name, product_name, production_quantity, total_cost, request_date)
        )
        request_id = cursor.lastrowid
        
        # 2. Get unit info for line items (already in line_items cache)
        
        # 3. Insert line items
        items_to_insert = []
        for item in line_items:
            if item['quantity_needed'] > 0: # Only save items that need to be ordered
                unit = item.get('unit_of_measure', 'pcs') # Use the unit from the cache
                items_to_insert.append((
                    request_id,
                    item['material_name'],
                    item['quantity_needed'],
                    unit,
                    item['cost']
                ))
        
        if items_to_insert:
            cursor.executemany(
                """
                INSERT INTO request_line_items (request_id, material_name, quantity_needed, unit_of_measure, cost)
                VALUES (?, ?, ?, ?, ?)
                """,
                items_to_insert
            )
        
        conn.commit()
        return request_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def add_completed_material_order(employee_id, employee_name, product_name, production_quantity, total_cost, line_items):
    """Saves a 'completed' order to the local employee log."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        # 1. Insert the main order
        completion_date = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO completed_material_orders 
            (employee_id, employee_name, product_name, production_quantity, total_cost, completion_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (employee_id, employee_name, product_name, production_quantity, total_cost, completion_date)
        )
        order_id = cursor.lastrowid
        
        # 2. Insert line items
        items_to_insert = []
        for item in line_items:
            if item['quantity_needed'] > 0: # Only save items that need to be ordered
                items_to_insert.append((
                    order_id,
                    item['material_name'],
                    item['quantity_needed'],
                    item['cost']
                ))
        
        if items_to_insert:
            cursor.executemany(
                """
                INSERT INTO completed_order_line_items (order_id, material_name, quantity_needed, cost)
                VALUES (?, ?, ?, ?)
                """,
                items_to_insert
            )
        
        conn.commit()
        return order_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_all_material_requests():
    """Fetches all material requests for the admin dashboard."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM material_requests ORDER BY request_date DESC")
    requests = cursor.fetchall()
    conn.close()
    return [dict(row) for row in requests]

def get_material_requests_by_employee(employee_id):
    """Fetches all material requests submitted by a specific employee."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM material_requests WHERE employee_id = ? ORDER BY request_date DESC",
        (employee_id,)
    )
    requests = cursor.fetchall()
    conn.close()
    return [dict(row) for row in requests]

def get_request_line_items(request_id):
    """Fetches the line items for a single material request."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM request_line_items WHERE request_id = ?", (request_id,))
    items = cursor.fetchall()
    conn.close()
    return [dict(row) for row in items]
    
def update_request_status(request_id, new_status):
    """Updates the status of a material request (Pending, Approved, Rejected, Completed)."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE material_requests SET status = ? WHERE request_id = ?", (new_status, request_id)) # <-- UPDATED
    conn.commit()
    conn.close()

def delete_material_request(request_id):
    """Permanently deletes a material request and its line items (due to ON DELETE CASCADE)."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM material_requests WHERE request_id = ?", (request_id,)) # <-- UPDATED
    conn.commit()
    conn.close()

def receive_material_request_stock(request_id):
    """
    Receives stock from an approved request:
    1. Fetches all line items for the request.
    2. Adds the 'quantity_needed' to the 'stock' in the main materials table.
    3. Updates the request status to 'Completed'.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        # 1. Get line items
        line_items = get_request_line_items(request_id) # Uses a separate connection, which is fine
        
        if not line_items:
            raise Exception("No line items found for this request.")
            
        # 2. Update stock for each item
        for item in line_items:
            cursor.execute(
                """
                UPDATE materials
                SET stock = stock + ?
                WHERE name = ?
                """,
                (item['quantity_needed'], item['material_name'])
            )
        
        # 3. Update request status
        cursor.execute("UPDATE material_requests SET status = 'Completed' WHERE request_id = ?", (request_id,)) # <-- UPDATED
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# --- Data Import (from CSV) --- (UPDATED)

def import_sales_from_csv(file_path):
    """
    Reads the NEW, CLEAN sales CSV, cleans it, and loads it into the database.
    This replaces all existing "historical" data.
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        raise
    except Exception as e:
        print(f"Error reading CSV: {e}")
        raise

    # Clean column names (remove leading/trailing spaces)
    df.columns = df.columns.str.strip()
    
    # --- Data Cleaning (SIMPLIFIED) ---
    # The 'product_name' is now just the 'Category'
    df['product_name'] = df['Category']
    # --- END SIMPLIFIED ---
    
    # Melt the DataFrame to long format
    months = [
        'January', 'February', 'March', 'April', 'May', 'June', 
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    df_melted = df.melt(
        id_vars=['product_name'],
        value_vars=months,
        var_name='month_name',
        value_name='quantity'
    )
    
    # Convert month names to numbers
    month_map = {name: i+1 for i, name in enumerate(months)}
    df_melted['month'] = df_melted['month_name'].map(month_map)
    
    # Clean quantity (remove commas, NaNs, convert to int)
    df_melted['quantity'] = pd.to_numeric(
        df_melted['quantity'].astype(str).str.replace(',', ''), 
        errors='coerce'
    ).fillna(0).astype(int)
    
    # Add year (hardcoded as 2024 as per user request)
    df_melted['year'] = 2024
    
    # Group by product, year, month to sum up duplicates
    final_sales = df_melted.groupby(['product_name', 'year', 'month'])['quantity'].sum().reset_index()
    
    # Add the flag for "historical" data
    final_sales['is_historical_csv'] = 1

    # --- Database Transaction ---
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        # Clear ALL old historical data (is_historical_csv=1)
        cursor.execute("DELETE FROM sales_history WHERE is_historical_csv = 1")
        
        # Insert new data
        final_sales.to_sql('sales_history', conn, if_exists='append', index=False)
        
        conn.commit()
        print(f"Successfully imported {len(final_sales)} historical sales records.")
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# --- Main execution ---
if __name__ == '__main__':
    init_db()