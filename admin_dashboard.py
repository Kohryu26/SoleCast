import sys
import pandas as pd
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QComboBox,
    QLabel, QPushButton, QFormLayout, QHBoxLayout, QMessageBox,
    QCalendarWidget, QLineEdit, QDialog, QDialogButtonBox,
    QFileDialog, QAbstractItemView, QGroupBox, QGridLayout,
    QTextEdit
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor

import database
import reporting
import forecasting_model # This is the scikit-learn model
from datetime import datetime

# --- Password Reset Dialog ---
class ResetPasswordDialog(QDialog):
    """A dialog box for securely resetting a user's password."""
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Reset Password for {username}")
        self.username = username
        
        self.layout = QFormLayout(self)
        
        self.info_label = QLabel(f"Enter a new password for <b>{self.username}</b>:")
        self.layout.addRow(self.info_label)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addRow("New Password:", self.new_password_input)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addRow("Confirm Password:", self.confirm_password_input)
        
        # Standard buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addRow(self.buttons)
        
    def get_password(self):
        """Returns the new password if it's valid."""
        new_pass = self.new_password_input.text()
        confirm_pass = self.confirm_password_input.text()
        
        if not new_pass or not confirm_pass:
            QMessageBox.warning(self, "Error", "Both fields are required.")
            return None
            
        if new_pass != confirm_pass:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return None
            
        if len(new_pass) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters long.")
            return None
            
        return new_pass

# --- Main Admin Dashboard ---

class AdminDashboard(QMainWindow):
    logged_out = Signal()

    def __init__(self, user_id, username):
        super().__init__()
        self.user_id = user_id
        self.username = username
        
        self.setWindowTitle(f"SoleCast Admin Dashboard - Welcome, {self.username}")
        self.setGeometry(100, 100, 1400, 900)
        
        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        self.setCentralWidget(self.tabs)
        
        # Caches for product and material lists
        self.product_list = []
        self.material_list = []
        
        self.setup_tabs()
        self.load_styles()
        
        # Load initial data
        self.refresh_product_and_material_lists()
        
    def setup_tabs(self):
        """Initializes all the tabs for the dashboard."""
        self.tabs.addTab(self.create_welcome_tab(), "Welcome")
        self.tabs.addTab(self.create_users_tab(), "Manage Accounts (2)")
        self.tabs.addTab(self.create_materials_tab(), "Manage Materials (3)")
        self.tabs.addTab(self.create_bom_tab(), "Manage BOM (8)")
        self.tabs.addTab(self.create_sales_tab(), "Handle Sales (7)")
        self.tabs.addTab(self.create_targets_tab(), "Manage Targets (4)")
        # --- COMBINED TABS ---
        self.tabs.addTab(self.create_forecast_kpi_tab(), "Forecast & KPIs (5, 6)")
        # --- END COMBINED TABS ---
        self.tabs.addTab(self.create_requests_tab(), "Material Requests")
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
    def on_tab_changed(self, index):
        """Loads data for the currently selected tab."""
        tab_title = self.tabs.tabText(index)
        
        # Refresh lists in case data was imported
        self.refresh_product_and_material_lists()
        
        if "Manage Accounts" in tab_title:
            self.load_users_data()
        elif "Manage Materials" in tab_title:
            self.load_materials_data()
        elif "Manage BOM" in tab_title:
            self.load_bom_data()
        elif "Manage Targets" in tab_title:
            self.load_targets_data()
        # --- UPDATED ---
        elif "Forecast & KPIs" in tab_title:
            # Load product list for forecast tab
            self.forecast_product_combo.clear()
            self.forecast_product_combo.addItems(self.product_list)
            # KPI product list is no longer needed, it's tab-based
        # --- END UPDATE ---
        elif "Material Requests" in tab_title:
            self.load_material_requests()
        elif "Handle Sales" in tab_title:
            # Refresh product list for the sales tab
            self.sales_product_combo.clear()
            self.sales_product_combo.addItems(self.product_list)
            
    def refresh_product_and_material_lists(self):
        """
        Refreshes the cached lists of products and materials.
        This is a central place to get fresh data after imports.
        """
        try:
            # Get products from sales history
            sales_df = database.get_sales_history()
            if sales_df.empty:
                self.product_list = ["(No products)"]
            else:
                self.product_list = sorted(list(sales_df['product_name'].unique()))
                
            # Get materials
            materials = database.get_all_materials()
            if not materials:
                self.material_list = ["(No materials)"]
            else:
                self.material_list = sorted([m['name'] for m in materials])
                
        except Exception as e:
            print(f"Error refreshing lists: {e}")
            self.product_list = ["(Error)"]
            self.material_list = ["(Error)"]

    # --- Tab 1: Welcome (No Process) ---
    def create_welcome_tab(self):
        """Creates the welcome tab with general info and logout."""
        widget = QWidget()
        welcome_layout = QVBoxLayout(widget)
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        welcome_layout.setContentsMargins(50, 50, 50, 50)
        welcome_layout.setSpacing(20)

        title = QLabel("SoleCast: Admin Dashboard")
        title.setObjectName("WelcomeTitle")
        
        info = QLabel(f"""
        Welcome, <b>{self.username}</b>.
        
        You have administrative privileges. You can manage user accounts,
        import data, manage materials, and oversee all production targets
        and requests.
        """)
        info.setObjectName("WelcomeInfo")
        info.setWordWrap(True)

        welcome_layout.addWidget(title)
        welcome_layout.addWidget(info)
        welcome_layout.addStretch() # Pushes the button to the bottom
        
        # Logout Button
        self.logout_button = QPushButton("Log Out")
        self.logout_button.setObjectName("LogoutButton")
        self.logout_button.clicked.connect(self.handle_logout)
        
        # Align button to the right
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.logout_button)
        welcome_layout.addLayout(button_layout)
        
        return widget
        
    def handle_logout(self):
        """Emits the logged_out signal."""
        self.logged_out.emit()
    
    def import_sales_csv(self):
        """Opens a dialog to import the historical sales CSV."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Historical Sales CSV", "", "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            database.import_sales_from_csv(file_path)
            QMessageBox.information(
                self, "Success", 
                "Successfully imported historical sales data.\n"
                "The product list has been updated."
            )
            # Refresh lists to show new products
            self.refresh_product_and_material_lists()
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Could not import sales CSV: {e}")

    # --- Tab 3: Manage Accounts (Process 2) ---
    def create_users_tab(self):
        """Creates the 'Manage Employee Accounts' tab UI."""
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- Left Side: User List ---
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Existing Users", objectName="FormTitle"))
        
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(3)
        self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Role"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.users_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        left_layout.addWidget(self.users_table)
        main_layout.addLayout(left_layout, 2)
        
        # --- Right Side: Controls ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Create New User ---
        create_group = QGroupBox("Create New User")
        create_layout = QFormLayout(create_group)
        
        self.new_username_input = QLineEdit()
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_role_combo = QComboBox()
        self.new_role_combo.addItems(["Admin", "Employee"])
        self.create_user_button = QPushButton("Create User")
        self.create_user_button.clicked.connect(self.create_new_user)
        
        create_layout.addRow("Username:", self.new_username_input)
        create_layout.addRow("Password:", self.new_password_input)
        create_layout.addRow("Role:", self.new_role_combo)
        create_layout.addRow(self.create_user_button)
        
        right_layout.addWidget(create_group)
        
        # --- Manage Selected User ---
        manage_group = QGroupBox("Manage Selected User")
        manage_layout = QVBoxLayout(manage_group)
        manage_layout.setSpacing(10)
        
        manage_label = QLabel("Select a user from the table to manage.")
        manage_label.setObjectName("InfoText")
        
        # Reset Password
        self.reset_password_button = QPushButton("Reset Selected User's Password")
        self.reset_password_button.clicked.connect(self.reset_password)
        
        # Update Role
        self.update_role_button = QPushButton("Set Selected User to 'Employee'")
        self.update_role_button.clicked.connect(lambda: self.update_role('Employee'))
        
        self.update_role_admin_button = QPushButton("Set Selected User to 'Admin'")
        self.update_role_admin_button.clicked.connect(lambda: self.update_role('Admin'))
        
        # Delete User
        self.delete_user_button = QPushButton("Delete Selected User")
        self.delete_user_button.setObjectName("DeleteButton")
        self.delete_user_button.clicked.connect(self.delete_user)
        
        manage_layout.addWidget(manage_label)
        manage_layout.addWidget(self.reset_password_button)
        manage_layout.addWidget(self.update_role_button)
        manage_layout.addWidget(self.update_role_admin_button)
        manage_layout.addWidget(self.delete_user_button)
        
        right_layout.addWidget(manage_group)
        right_layout.addStretch()
        main_layout.addLayout(right_layout, 1)

        return widget

    def get_selected_user(self):
        """Helper to get the selected user ID and username from the table."""
        selected_rows = self.users_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No User Selected", "Please select a user from the table first.")
            return None, None
            
        selected_row = selected_rows[0].row()
        user_id = int(self.users_table.item(selected_row, 0).text())
        username = self.users_table.item(selected_row, 1).text()
        
        # Prevent admin from deleting/demoting themselves
        if user_id == self.user_id:
            QMessageBox.critical(self, "Action Not Allowed", "You cannot modify your own account.")
            return None, None
            
        return user_id, username

    def load_users_data(self):
        """Loads all user data into the table."""
        try:
            users = database.get_all_users()
            self.users_table.setRowCount(len(users))
            for row, user in enumerate(users):
                # --- THIS IS THE FIX ---
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user['user_id'])))
                # --- END FIX ---
                self.users_table.setItem(row, 1, QTableWidgetItem(user['username']))
                self.users_table.setItem(row, 2, QTableWidgetItem(user['role']))
                
                # Gray out the current admin's row to show it can't be modified
                if user['user_id'] == self.user_id: # <-- FIXED
                    for col in range(3):
                        self.users_table.item(row, col).setBackground(QColor("#f0f0f0"))
                        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load users: {e}")
            
    def create_new_user(self):
        """Creates a new user from the form inputs."""
        username = self.new_username_input.text()
        password = self.new_password_input.text()
        role = self.new_role_combo.currentText()
        
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Username and password are required.")
            return
            
        if len(password) < 6:
            QMessageBox.warning(self, "Input Error", "Password must be at least 6 characters long.")
            return
            
        try:
            database.add_new_user(username, password, role)
            QMessageBox.information(self, "Success", f"User '{username}' created successfully.")
            self.load_users_data() # Refresh table
            # Clear inputs
            self.new_username_input.clear()
            self.new_password_input.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create user: {e}")

    def reset_password(self):
        """Resets the password for the selected user."""
        user_id, username = self.get_selected_user()
        if not user_id:
            return
            
        # Open the reset password dialog
        dialog = ResetPasswordDialog(username, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_password = dialog.get_password()
            if new_password:
                try:
                    # We use username to update, not ID, as per DB function
                    database.update_user_password(username, new_password)
                    QMessageBox.information(self, "Success", f"Password for '{username}' has been reset.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not reset password: {e}")

    def update_role(self, new_role):
        """Updates the role for the selected user."""
        user_id, username = self.get_selected_user()
        if not user_id:
            return
            
        try:
            database.update_user_role(user_id, new_role)
            QMessageBox.information(self, "Success", f"User '{username}' role updated to '{new_role}'.")
            self.load_users_data() # Refresh table
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update role: {e}")
            
    def delete_user(self):
        """Deletes the selected user."""
        user_id, username = self.get_selected_user()
        if not user_id:
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the user '{username}'?\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                database.delete_user(user_id)
                QMessageBox.information(self, "Success", f"User '{username}' has been deleted.")
                self.load_users_data() # Refresh table
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete user: {e}")

    # --- Tab 4: Manage Materials (Process 3) ---
    def create_materials_tab(self):
        """Creates the 'Manage Materials Stock' tab UI."""
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- Left Side: Materials List ---
        left_layout = QVBoxLayout()
        
        # Filter dropdown
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Product:"))
        self.material_filter_combo = QComboBox()
        self.material_filter_combo.addItems(["All", "P.E.", "Slip-on"]) # "Common" removed
        self.material_filter_combo.currentTextChanged.connect(self.load_materials_data)
        filter_layout.addWidget(self.material_filter_combo)
        
        # --- NEW: Import Button ---
        filter_layout.addStretch()
        self.import_materials_button = QPushButton("Import Materials CSV")
        self.import_materials_button.clicked.connect(self.import_materials_csv)
        filter_layout.addWidget(self.import_materials_button)
        # --- END NEW ---
        
        left_layout.addLayout(filter_layout)
        
        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(6)
        self.materials_table.setHorizontalHeaderLabels(["ID", "Name", "Stock", "Unit", "Price/Unit (₱)", "Product"])
        self.materials_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.materials_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.materials_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.materials_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.materials_table.selectionModel().selectionChanged.connect(self.on_material_selected)
        
        left_layout.addWidget(self.materials_table)
        main_layout.addLayout(left_layout, 2)
        
        # --- Right Side: Controls ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Add/Edit Material ---
        form_group = QGroupBox("Add / Edit Material")
        form_layout = QFormLayout(form_group)
        
        self.material_id_label = QLabel("(New Material)")
        self.material_name_input = QLineEdit()
        
        # Stock and Price layout
        stock_price_layout = QHBoxLayout()
        self.material_stock_spinbox = QSpinBox(minimum=0, maximum=1000000)
        self.material_stock_spinbox.valueChanged.connect(self.update_total_cost)
        self.material_unit_combo = QComboBox()
        self.material_unit_combo.addItems(["pcs", "pairs", "meters", "sq. ft.", "liters", "kg"])
        stock_price_layout.addWidget(self.material_stock_spinbox, 2) # 2/3 width
        stock_price_layout.addWidget(self.material_unit_combo, 1) # 1/3 width
        
        price_layout = QHBoxLayout()
        self.material_price_spinbox = QSpinBox(minimum=0, maximum=1000000)
        self.material_price_spinbox.setPrefix("₱ ")
        self.material_price_spinbox.valueChanged.connect(self.update_total_cost)
        
        self.material_total_cost_label = QLabel("₱ 0")
        self.material_total_cost_label.setObjectName("TotalCostLabel")
        price_layout.addWidget(self.material_price_spinbox, 1)
        price_layout.addWidget(QLabel("Total Cost:"))
        price_layout.addWidget(self.material_total_cost_label, 1)

        self.material_assoc_combo = QComboBox()
        self.material_assoc_combo.addItems(["P.E.", "Slip-on"]) # "Common" removed
        
        form_layout.addRow("ID:", self.material_id_label)
        form_layout.addRow("Name:", self.material_name_input)
        form_layout.addRow("Stock / Unit:", stock_price_layout)
        form_layout.addRow("Price/Unit:", price_layout)
        form_layout.addRow("Product:", self.material_assoc_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_material_button = QPushButton("Save (Add New / Update)")
        self.save_material_button.clicked.connect(self.save_material)
        self.clear_material_form_button = QPushButton("Clear Form")
        self.clear_material_form_button.clicked.connect(self.clear_material_form)
        button_layout.addWidget(self.save_material_button)
        button_layout.addWidget(self.clear_material_form_button)
        form_layout.addRow(button_layout)
        
        # Delete Button
        self.delete_material_button = QPushButton("Delete Selected Material")
        self.delete_material_button.setObjectName("DeleteButton")
        self.delete_material_button.clicked.connect(self.delete_material)
        self.delete_material_button.setEnabled(False) # Enable on selection
        
        right_layout.addWidget(form_group)
        right_layout.addWidget(self.delete_material_button)
        right_layout.addStretch()
        main_layout.addLayout(right_layout, 1)

        return widget
        
    def update_total_cost(self):
        """Calculates and displays the total cost in the material form."""
        try:
            stock = self.material_stock_spinbox.value()
            price = self.material_price_spinbox.value()
            total_cost = stock * price
            self.material_total_cost_label.setText(f"₱ {total_cost:,.0f}")
        except Exception:
            self.material_total_cost_label.setText("₱ 0") # Handle potential errors

    def load_materials_data(self):
        """Loads all material data into the table, applying filter."""
        try:
            materials = database.get_all_materials()
            self.materials_table.setRowCount(0) # Clear table
            
            filter_text = self.material_filter_combo.currentText()
            
            for material in materials:
                if filter_text == "All" or material['product_association'] == filter_text:
                    row = self.materials_table.rowCount()
                    self.materials_table.insertRow(row)
                    
                    self.materials_table.setItem(row, 0, QTableWidgetItem(str(material['material_id']))) # <-- FIXED
                    self.materials_table.setItem(row, 1, QTableWidgetItem(material['name']))
                    self.materials_table.setItem(row, 2, QTableWidgetItem(str(material['stock'])))
                    self.materials_table.setItem(row, 3, QTableWidgetItem(material['unit_of_measure'])) # <-- NEW
                    self.materials_table.setItem(row, 4, QTableWidgetItem(f"{material['price']:.2f}"))
                    self.materials_table.setItem(row, 5, QTableWidgetItem(material['product_association']))
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load materials: {e}")

    def on_material_selected(self):
        """Populates the form when a material is selected from the table."""
        selected_rows = self.materials_table.selectionModel().selectedRows()
        if not selected_rows:
            self.clear_material_form()
            return
            
        selected_row = selected_rows[0].row()
        
        # Get data from table
        mat_id = self.materials_table.item(selected_row, 0).text()
        name = self.materials_table.item(selected_row, 1).text()
        stock = int(self.materials_table.item(selected_row, 2).text())
        unit = self.materials_table.item(selected_row, 3).text()
        price_str = self.materials_table.item(selected_row, 4).text().replace("₱", "").replace(",", "")
        price = int(float(price_str))
        assoc = self.materials_table.item(selected_row, 5).text()
        
        # Populate form
        self.material_id_label.setText(mat_id)
        self.material_name_input.setText(name)
        self.material_stock_spinbox.setValue(stock)
        self.material_unit_combo.setCurrentText(unit)
        self.material_price_spinbox.setValue(price)
        self.material_assoc_combo.setCurrentText(assoc)
        
        self.delete_material_button.setEnabled(True)
        self.update_total_cost() # Update total cost label

    def clear_material_form(self):
        """Clears the material form to '(New Material)' state."""
        self.material_id_label.setText("(New Material)")
        self.material_name_input.clear()
        self.material_stock_spinbox.setValue(0)
        self.material_price_spinbox.setValue(0)
        self.material_unit_combo.setCurrentIndex(0) # "pcs"
        self.material_assoc_combo.setCurrentIndex(0) # "P.E."
        
        self.materials_table.clearSelection()
        self.delete_material_button.setEnabled(False)
        self.update_total_cost() # Reset total cost label

    def save_material(self):
        """Saves a new or existing material."""
        material_id = self.material_id_label.text()
        name = self.material_name_input.text()
        stock = self.material_stock_spinbox.value()
        price = self.material_price_spinbox.value()
        assoc = self.material_assoc_combo.currentText()
        unit = self.material_unit_combo.currentText() # <-- NEW
        
        if not name:
            QMessageBox.warning(self, "Input Error", "Material name is required.")
            return
            
        try:
            if material_id == "(New Material)":
                # Add new
                database.add_material(name, stock, price, assoc, unit)
                QMessageBox.information(self, "Success", f"Material '{name}' added.")
            else:
                # Update existing
                database.update_material(int(material_id), name, stock, price, assoc, unit)
                QMessageBox.information(self, "Success", f"Material '{name}' updated.")
                
            self.load_materials_data() # Refresh table
            self.clear_material_form()
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: materials.name" in str(e):
                QMessageBox.critical(self, "Error", f"Could not save material: The name '{name}' already exists.")
            else:
                QMessageBox.critical(self, "Error", f"Could not save material: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save material: {e}")

    def delete_material(self):
        """Deletes the selected material."""
        material_id = self.material_id_label.text()
        name = self.material_name_input.text()
        
        if material_id == "(New Material)":
            return # Should be disabled, but as a safeguard
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the material '{name}'?\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                database.delete_material(int(material_id))
                QMessageBox.information(self, "Success", f"Material '{name}' has been deleted.")
                self.load_materials_data() # Refresh table
                self.clear_material_form()
            except Exception as e:
                # Check for foreign key constraint (if material is in a BOM)
                if "FOREIGN KEY" in str(e):
                    QMessageBox.critical(self, "Error", 
                        f"Cannot delete '{name}': It is currently being used in a Bill of Materials.\n"
                        "Please remove it from the BOM first.")
                else:
                    QMessageBox.critical(self, "Error", f"Could not delete material: {e}")

    def import_materials_csv(self):
        """Opens a dialog to import the materials CSV."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Materials CSV", "", "CSV Files (*.csv)"
        )
        if not file_path:
            return
            
        try:
            df = pd.read_csv(file_path)
            # Check for required columns
            required_cols = ['name', 'stock', 'price', 'product_association', 'unit_of_measure']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV must contain all columns: {required_cols}")
                
            imported_count = 0
            for _, row in df.iterrows():
                database.upsert_material_from_csv(
                    row['name'],
                    row['stock'],
                    row['price'],
                    row['product_association'],
                    row['unit_of_measure']
                )
                imported_count += 1
            
            QMessageBox.information(
                self, "Success", 
                f"Successfully imported/updated {imported_count} materials.\n"
                "The material list has been updated."
            )
            # Refresh lists
            self.refresh_product_and_material_lists()
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Could not import materials CSV: {e}")

    # --- Tab 5: Manage BOM (Process 8) ---
    def create_bom_tab(self):
        """Creates the 'Manage Bill of Materials' tab UI."""
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Left Side: BOM List ---
        left_layout = QVBoxLayout()
        
        # --- NEW: Filter ---
        bom_filter_layout = QHBoxLayout()
        bom_filter_layout.addWidget(QLabel("Filter by Product:"))
        self.bom_filter_combo = QComboBox()
        self.bom_filter_combo.currentTextChanged.connect(self.load_bom_data)
        bom_filter_layout.addWidget(self.bom_filter_combo)
        bom_filter_layout.addStretch()
        left_layout.addLayout(bom_filter_layout)
        # --- END NEW ---
        
        self.bom_table = QTableWidget()
        self.bom_table.setColumnCount(5)
        self.bom_table.setHorizontalHeaderLabels(["ID", "Product Name", "Material Name", "Qty Per Unit", "Unit"])
        self.bom_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bom_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.bom_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bom_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        left_layout.addWidget(self.bom_table)
        main_layout.addLayout(left_layout, 2)
        
        # --- Right Side: Controls ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # --- Add BOM Item ---
        form_group = QGroupBox("Add / Update BOM Item")
        form_layout = QFormLayout(form_group)
        
        self.bom_product_combo = QComboBox()
        self.bom_material_combo = QComboBox()
        self.bom_quantity_spinbox = QSpinBox(minimum=1, maximum=1000)
        
        form_layout.addRow("Product:", self.bom_product_combo)
        form_layout.addRow("Material:", self.bom_material_combo)
        form_layout.addRow("Quantity per Unit:", self.bom_quantity_spinbox)
        
        self.save_bom_item_button = QPushButton("Save BOM Item")
        self.save_bom_item_button.clicked.connect(self.save_bom_item)
        form_layout.addRow(self.save_bom_item_button)
        
        # --- Delete BOM Item ---
        delete_group = QGroupBox("Delete BOM Item")
        delete_layout = QVBoxLayout(delete_group)
        delete_layout.setSpacing(10)
        
        delete_label = QLabel("Select an item from the table and click Delete.")
        delete_label.setObjectName("InfoText")
        
        self.delete_bom_item_button = QPushButton("Delete Selected BOM Item")
        self.delete_bom_item_button.setObjectName("DeleteButton")
        self.delete_bom_item_button.clicked.connect(self.delete_bom_item)
        
        delete_layout.addWidget(delete_label)
        delete_layout.addWidget(self.delete_bom_item_button)
        
        right_layout.addWidget(form_group)
        right_layout.addWidget(delete_group)
        right_layout.addStretch()
        main_layout.addLayout(right_layout, 1)

        return widget

    def load_bom_data(self):
        """Loads BOM data into the table and populates dropdowns."""
        # Populate dropdowns first
        # Filter dropdown (add "All")
        # --- FIX: Check if items exist before clearing ---
        if self.bom_filter_combo.count() == 0:
            self.bom_filter_combo.addItems(["All"] + self.product_list)
        # --- END FIX ---
        
        # Form dropdowns (no "All")
        self.bom_product_combo.clear()
        self.bom_product_combo.addItems(self.product_list)
        self.bom_material_combo.clear()
        self.bom_material_combo.addItems(self.material_list)
        
        # Load table data
        try:
            bom_items = database.get_full_bom()
            self.bom_table.setRowCount(0) # Clear table
            
            filter_text = self.bom_filter_combo.currentText()
            
            for item in bom_items:
                if filter_text == "All" or item['product_name'] == filter_text:
                    row = self.bom_table.rowCount()
                    self.bom_table.insertRow(row)
                    
                    self.bom_table.setItem(row, 0, QTableWidgetItem(str(item['bom_id']))) # <-- FIXED
                    self.bom_table.setItem(row, 1, QTableWidgetItem(item['product_name']))
                    self.bom_table.setItem(row, 2, QTableWidgetItem(item['material_name']))
                    self.bom_table.setItem(row, 3, QTableWidgetItem(str(item['quantity_per_unit'])))
                    self.bom_table.setItem(row, 4, QTableWidgetItem(item['unit_of_measure'])) # <-- NEW
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load BOM: {e}")

    def save_bom_item(self):
        """Saves a new or updated BOM item."""
        product_name = self.bom_product_combo.currentText()
        material_name = self.bom_material_combo.currentText()
        quantity = self.bom_quantity_spinbox.value()
        
        if "(No products)" in product_name or "(No materials)" in material_name:
            QMessageBox.warning(self, "Input Error", "Please import products and materials first.")
            return
            
        try:
            database.add_bom_item(product_name, material_name, quantity)
            QMessageBox.information(
                self, "Success", 
                f"BOM item saved:\n{product_name} -> {quantity} x {material_name}"
            )
            self.load_bom_data() # Refresh table
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save BOM item: {e}")

    def delete_bom_item(self):
        """Deletes the selected BOM item from the table."""
        selected_rows = self.bom_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Item Selected", "Please select a BOM item from the table first.")
            return
            
        selected_row = selected_rows[0].row()
        bom_item_id = int(self.bom_table.item(selected_row, 0).text())
        item_name = f"{self.bom_table.item(selected_row, 1).text()} -> {self.bom_table.item(selected_row, 2).text()}"
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the BOM item:\n{item_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                database.delete_bom_item(bom_item_id)
                QMessageBox.information(self, "Success", f"BOM item '{item_name}' has been deleted.")
                self.load_bom_data() # Refresh table
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete BOM item: {e}")

    # --- Tab 6: Handle Sales (Process 7) --- (UPDATED)
    def create_sales_tab(self):
        """Creates the 'Handle Sales' tab UI (moved to Admin)."""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- NEW: Import Sales History ---
        import_group = QGroupBox("Import Historical Sales")
        import_layout = QVBoxLayout(import_group)
        
        import_label = QLabel(
            "Import the historical sales data from a CSV file.\n"
            "This is the **first step** and will populate your product list."
        )
        import_label.setWordWrap(True)
        self.import_sales_button = QPushButton("Import Historical Sales CSV")
        self.import_sales_button.clicked.connect(self.import_sales_csv)
        
        import_layout.addWidget(import_label)
        import_layout.addWidget(self.import_sales_button)
        main_layout.addWidget(import_group)
        
        # --- Form for adding sales ---
        sales_group = QGroupBox("Add Current Sales Data")
        sales_group.setObjectName("FormGroup")
        sales_layout = QFormLayout(sales_group)
        sales_layout.setSpacing(10)
        
        sales_label = QLabel("Add a new entry for current year sales.")
        sales_label.setObjectName("FormTitle")
        
        self.sales_product_combo = QComboBox()
        self.sales_calendar = QCalendarWidget()
        self.sales_calendar.setSelectedDate(QDate.currentDate())
        self.sales_calendar.setMaximumDate(QDate.currentDate())
        self.sales_calendar.setGridVisible(True)
        
        self.sales_quantity_spinbox = QSpinBox(minimum=1, maximum=100000)
        self.add_sales_button = QPushButton("Add Sales Entry")
        self.add_sales_button.clicked.connect(self.add_sales_data)
        
        sales_layout.addRow(sales_label)
        sales_layout.addRow("Product:", self.sales_product_combo)
        sales_layout.addRow("Date:", self.sales_calendar)
        sales_layout.addRow("Quantity Sold:", self.sales_quantity_spinbox)
        sales_layout.addRow(self.add_sales_button)
        
        main_layout.addWidget(sales_group)
        main_layout.addStretch()

        return widget

    def add_sales_data(self):
        """Adds a new (current) sales entry to the database."""
        product_name = self.sales_product_combo.currentText()
        date = self.sales_calendar.selectedDate().toPyDate()
        quantity = self.sales_quantity_spinbox.value()
        
        if "(No products)" in product_name:
            QMessageBox.warning(self, "Input Error", "No products available. Please import sales data first.")
            return

        try:
            database.add_sales_entry(product_name, date.year, date.month, quantity)
            QMessageBox.information(self, "Success", f"Added {quantity} sales for {product_name} on {date.strftime('%Y-%m')}.")
            self.sales_quantity_spinbox.setValue(1)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not add sales data: {e}")

    # --- Tab 7: Manage Targets (Process 4) ---
    def create_targets_tab(self):
        """Creates the 'Manage Production Targets' tab UI."""
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Left Side: Target List ---
        left_layout = QVBoxLayout()
        
        # --- NEW: Import Button ---
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Production Targets", objectName="FormTitle"))
        header_layout.addStretch()
        self.import_targets_button = QPushButton("Import Targets CSV")
        self.import_targets_button.clicked.connect(self.import_targets_csv)
        header_layout.addWidget(self.import_targets_button)
        left_layout.addLayout(header_layout)
        # --- END NEW ---
        
        self.targets_table = QTableWidget()
        self.targets_table.setColumnCount(6)
        # --- UPDATED HEADERS ---
        self.targets_table.setHorizontalHeaderLabels(["Target ID", "Product", "Year", "Month", "Target Quantity (pairs)", "Target Increase (%)"])
        # --- END UPDATE ---
        self.targets_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.targets_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.targets_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.targets_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        left_layout.addWidget(self.targets_table)
        main_layout.addLayout(left_layout, 2)
        
        # --- Right Side: Controls ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # --- Add/Edit Target ---
        form_group = QGroupBox("Add / Update Target")
        form_layout = QFormLayout(form_group)
        
        self.target_product_combo = QComboBox()
        self.target_year_spinbox = QSpinBox(minimum=2020, maximum=2050)
        self.target_year_spinbox.setValue(datetime.now().year)
        self.target_month_combo = QComboBox()
        self.target_month_combo.addItems([f"{i:02d}" for i in range(1, 13)])
        
        # --- UPDATED FORM ---
        self.target_quantity_spinbox = QSpinBox(minimum=0, maximum=10000000)
        self.target_quantity_spinbox.setSuffix(" pairs")
        
        self.target_increase_spinbox = QSpinBox(minimum=0, maximum=1000)
        # --- END UPDATE ---
        self.target_increase_spinbox.setSuffix(" %")
        
        self.save_target_button = QPushButton("Save Target")
        self.save_target_button.clicked.connect(self.save_target)
        
        form_layout.addRow("Product:", self.target_product_combo)
        form_layout.addRow("Year:", self.target_year_spinbox)
        form_layout.addRow("Month:", self.target_month_combo)
        # --- UPDATED FORM ---
        form_layout.addRow("Target Quantity:", self.target_quantity_spinbox)
        form_layout.addRow("Target Increase:", self.target_increase_spinbox)
        # --- END UPDATE ---
        form_layout.addRow(self.save_target_button)
        
        # --- Actual Consumption Report ---
        report_group = QGroupBox("Actual Material Consumption")
        report_layout = QFormLayout(report_group)
        
        report_label = QLabel("Calculates material usage based on 'Current Sales' and BOM.")
        report_label.setObjectName("InfoText")
        
        self.report_year_spinbox = QSpinBox(minimum=2020, maximum=2050)
        self.report_year_spinbox.setValue(datetime.now().year)
        self.report_month_combo = QComboBox()
        self.report_month_combo.addItems([f"{i:02d}" for i in range(1, 13)])
        self.report_month_combo.setCurrentText(f"{datetime.now().month:02d}")
        
        self.generate_consumption_report_button = QPushButton("Generate Report")
        self.generate_consumption_report_button.clicked.connect(self.generate_consumption_report)
        
        report_layout.addRow(report_label)
        report_layout.addRow("Year:", self.report_year_spinbox)
        report_layout.addRow("Month:", self.report_month_combo)
        report_layout.addRow(self.generate_consumption_report_button)
        
        right_layout.addWidget(form_group)
        right_layout.addWidget(report_group)
        right_layout.addStretch()
        main_layout.addLayout(right_layout, 1)

        return widget
        
    def load_targets_data(self):
        """Loads targets into the table and populates dropdown."""
        # Populate product dropdown
        self.target_product_combo.clear()
        self.target_product_combo.addItems(self.product_list)
        
        # Load table data
        try:
            targets_df = database.get_production_targets()
            if targets_df.empty:
                self.targets_table.setRowCount(0)
                return
                
            # Sort by year, month, product
            targets_df = targets_df.sort_values(by=['year', 'month', 'product_name'])
            
            self.targets_table.setRowCount(len(targets_df))
            for row, data in enumerate(targets_df.to_dict('records')):
                self.targets_table.setItem(row, 0, QTableWidgetItem(str(data['target_id']))) # <-- UPDATED
                self.targets_table.setItem(row, 1, QTableWidgetItem(data['product_name']))
                self.targets_table.setItem(row, 2, QTableWidgetItem(str(data['year'])))
                self.targets_table.setItem(row, 3, QTableWidgetItem(f"{data['month']:02d}"))
                # --- UPDATED TABLE DATA ---
                self.targets_table.setItem(row, 4, QTableWidgetItem(f"{data['target_quantity']:.0f} pairs"))
                self.targets_table.setItem(row, 5, QTableWidgetItem(f"{data['quota']:.1f} %"))
                # --- END UPDATE ---
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load targets: {e}")

    def save_target(self):
        """Saves a production target."""
        product_name = self.target_product_combo.currentText()
        year = self.target_year_spinbox.value()
        month = int(self.target_month_combo.currentText())
        # --- UPDATED LOGIC ---
        target_quantity = self.target_quantity_spinbox.value()
        target_increase = self.target_increase_spinbox.value()
        # --- END UPDATE ---
        
        if "(No products)" in product_name:
            QMessageBox.warning(self, "Input Error", "No products available.")
            return
            
        try:
            # --- UPDATED LOGIC ---
            database.save_production_target(product_name, year, month, target_quantity, target_increase)
            # --- END UPDATE ---
            QMessageBox.information(self, "Success", f"Target saved for {product_name} ({year}-{month:02d}).")
            self.load_targets_data() # Refresh table
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save target: {e}")

    def generate_consumption_report(self):
        """
        Generates a report on actual material consumption
        based on sales data and BOM (as per DFD Process 4).
        """
        year = self.report_year_spinbox.value()
        month = int(self.report_month_combo.currentText())
        
        try:
            # 1. Get current sales for the selected period
            sales_df = database.get_sales_history(is_historical_csv=False)
            if sales_df.empty:
                QMessageBox.information(self, "Report", "No current sales data found for any period.")
                return
                
            month_sales = sales_df[
                (sales_df['year'] == year) & (sales_df['month'] == month)
            ]
            
            if month_sales.empty:
                QMessageBox.information(self, "Report", f"No current sales data found for {year}-{month:02d}.")
                return
            
            # 2. Aggregate sales by product
            product_sales = month_sales.groupby('product_name')['quantity'].sum()
            
            # 3. Get full BOM
            bom_df = pd.DataFrame(database.get_full_bom())
            if bom_df.empty:
                QMessageBox.warning(self, "Report Error", "Cannot generate report: BOM is not defined.")
                return
            
            # 4. Calculate consumption
            consumption = {}
            for product_name, quantity_sold in product_sales.items():
                # Find materials for this product
                product_bom = bom_df[bom_df['product_name'] == product_name]
                for _, item in product_bom.iterrows():
                    mat_name = item['material_name']
                    qty_per_unit = item['quantity_per_unit']
                    unit = item['unit_of_measure']
                    total_mat_qty = qty_per_unit * quantity_sold
                    
                    # Add to consumption list
                    key = f"{mat_name} ({unit})"
                    if key not in consumption:
                        consumption[key] = 0
                    consumption[key] += total_mat_qty
            
            if not consumption:
                QMessageBox.information(self, "Report", f"No BOM items found for products sold in {year}-{month:02d}.")
                return

            # 5. Format and display the report
            report_text = f"<b>Actual Material Consumption for {year}-{month:02d}</b><br>"
            report_text += "Based on 'Current Sales' data.<br><br>"
            report_text += "<ul>"
            for mat_name_unit, total_qty in sorted(consumption.items()):
                report_text += f"<li><b>{mat_name_unit}:</b> {total_qty:,.0f} units</li>"
            report_text += "</ul>"
            
            # Show in a rich text dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Consumption Report")
            dialog_layout = QVBoxLayout(dialog)
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setHtml(report_text)
            dialog_layout.addWidget(text_edit)
            ok_button = QPushButton("OK")
            ok_button.clicked.connect(dialog.accept)
            dialog_layout.addWidget(ok_button)
            dialog.resize(400, 300)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Could not generate report: {e}")
            
    def import_targets_csv(self):
        """Opens a dialog to import the targets CSV."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Targets CSV", "", "CSV Files (*.csv)"
        )
        if not file_path:
            return
            
        try:
            df = pd.read_csv(file_path)
            # --- UPDATED CSV HEADERS ---
            required_cols = ['product_name', 'year', 'month', 'target_quantity', 'target_increase']
            # --- END UPDATE ---
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV must contain all columns: {required_cols}")
                
            imported_count = 0
            for _, row in df.iterrows():
                # --- UPDATED CSV LOGIC ---
                database.upsert_target_from_csv(
                    row['product_name'],
                    row['year'],
                    row['month'],
                    row['target_quantity'],
                    row['target_increase']
                )
                # --- END UPDATE ---
                imported_count += 1
            
            QMessageBox.information(
                self, "Success", 
                f"Successfully imported/updated {imported_count} targets."
            )
            self.load_targets_data() # Refresh list
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Could not import targets CSV: {e}")

    # --- Tab 8: Generate Forecasts (Process 5) --- (NOW COMBINED)
    
    # This function is now called by the new combined tab
    def run_forecast(self):
        """Generates and displays the sales forecast."""
        product_name = self.forecast_product_combo.currentText()
        percent_increase = self.forecast_increase_spinbox.value()
        # --- UPDATED: Target Year is now automatic ---
        target_year = datetime.now().year + 1
        # --- END UPDATE ---

        if "(No products)" in product_name:
            QMessageBox.warning(self, "Input Error", "No products available to forecast.")
            return
            
        try:
            # Get historical data
            historical_df = database.get_sales_history(is_historical_csv=True)
            if historical_df.empty:
                QMessageBox.warning(self, "No Data", "Cannot forecast: No historical data found.")
                return

            # Clear old predictions
            database.clear_predictions()

            # Generate forecast using the scikit-learn model
            forecast = forecasting_model.generate_sklearn_forecast(
                historical_df, 
                product_name,
                target_year,
                percent_increase
            )
            
            # Save new predictions
            for _, row in forecast.iterrows():
                database.save_prediction(
                    product_name,
                    row['year'],
                    row['month'],
                    row['predicted_quantity']
                )

            QMessageBox.information(self, "Success", f"Forecast generated and saved for {product_name}.")
            
            # --- NEW: Auto-refresh the KPI reports ---
            print("Forecast generated, refreshing KPI reports...")
            # Set the KPI year filter to the year we just forecasted
            self.kpi_year_spinbox.setValue(target_year)
            # --- UPDATED: Removed product combo filter ---
            # self.kpi_product_combo.setCurrentText(product_name) 
            # --- END UPDATE ---
            # Run the reports
            self.run_kpi_reports()
            
            # Also update the plot on the left
            reporting.plot_forecast_vs_actual(
                self.forecast_plot_canvas.axes,
                historical_df,
                forecast,
                product_name
            )
            self.forecast_plot_canvas.draw()
            
        except Exception as e:
            print(f"Error running forecast: {e}")
            QMessageBox.critical(self, "Error", f"Could not run forecast: {e}")

    # --- Tab 9: Material Requests ---
    def create_requests_tab(self):
        """Creates the 'Material Requests' tab UI for admin."""
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Left Side: Request List ---
        left_layout = QVBoxLayout()
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Material Requests", objectName="FormTitle"))
        header_layout.addStretch()
        self.refresh_requests_button = QPushButton("Refresh List")
        self.refresh_requests_button.clicked.connect(self.load_material_requests)
        header_layout.addWidget(self.refresh_requests_button)
        
        left_layout.addLayout(header_layout)
        
        self.requests_table = QTableWidget()
        self.requests_table.setColumnCount(7)
        self.requests_table.setHorizontalHeaderLabels(
            ["Req. ID", "Employee", "Product", "Qty", "Total Cost (₱)", "Status", "Date"]
        )
        self.requests_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.requests_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.requests_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.requests_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.requests_table.selectionModel().selectionChanged.connect(self.on_request_selected)
        
        left_layout.addWidget(self.requests_table)
        main_layout.addLayout(left_layout, 2)
        
        # --- Right Side: Details ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        details_group = QGroupBox("Request Details")
        details_layout = QVBoxLayout(details_group)
        
        self.request_details_label = QLabel("Select a request to see details.")
        self.request_details_label.setObjectName("InfoText")
        
        self.request_line_items_table = QTableWidget()
        self.request_line_items_table.setColumnCount(4)
        self.request_line_items_table.setHorizontalHeaderLabels(["Material", "Qty Needed", "Unit", "Cost"])
        self.request_line_items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # --- NEW Button Layout ---
        self.request_button_layout = QGridLayout()
        
        self.approve_button = QPushButton("Approve Request")
        self.approve_button.setEnabled(False)
        self.approve_button.clicked.connect(lambda: self.update_request_status("Approved"))
        
        self.reject_button = QPushButton("Reject Request")
        self.reject_button.setObjectName("DeleteButton") # Red style
        self.reject_button.setEnabled(False)
        self.reject_button.clicked.connect(lambda: self.update_request_status("Rejected"))
        
        self.receive_stock_button = QPushButton("Receive Stock & Complete")
        self.receive_stock_button.setEnabled(False)
        self.receive_stock_button.setObjectName("SendButton") # Green style
        self.receive_stock_button.clicked.connect(self.receive_stock_and_complete)
        
        self.delete_request_button = QPushButton("Delete Request")
        self.delete_request_button.setObjectName("DeleteButton")
        self.delete_request_button.setEnabled(False)
        self.delete_request_button.clicked.connect(self.delete_request)

        self.request_button_layout.addWidget(self.approve_button, 0, 0)
        self.request_button_layout.addWidget(self.reject_button, 0, 1)
        self.request_button_layout.addWidget(self.receive_stock_button, 1, 0, 1, 2)
        self.request_button_layout.addWidget(self.delete_request_button, 2, 0, 1, 2)
        # --- END NEW Button Layout ---
        
        details_layout.addWidget(self.request_details_label)
        details_layout.addWidget(self.request_line_items_table)
        details_layout.addLayout(self.request_button_layout)
        
        right_layout.addWidget(details_group)
        right_layout.addStretch()
        main_layout.addLayout(right_layout, 1)

        return widget

    def load_material_requests(self):
        """Loads all material requests into the table."""
        try:
            requests = database.get_all_material_requests()
            self.requests_table.setRowCount(len(requests))
            
            for row, req in enumerate(requests):
                self.requests_table.setItem(row, 0, QTableWidgetItem(str(req['request_id']))) # <-- FIXED
                self.requests_table.setItem(row, 1, QTableWidgetItem(req['employee_name']))
                self.requests_table.setItem(row, 2, QTableWidgetItem(req['product_name']))
                self.requests_table.setItem(row, 3, QTableWidgetItem(str(req['production_quantity'])))
                self.requests_table.setItem(row, 4, QTableWidgetItem(f"₱{req['total_cost']:.2f}"))
                
                status_item = QTableWidgetItem(req['status'])
                if req['status'] == 'Pending':
                    status_item.setForeground(QColor("#d9534f")) # Red
                elif req['status'] == 'Approved':
                    status_item.setForeground(QColor("#0275d8")) # Blue
                elif req['status'] == 'Completed':
                    status_item.setForeground(QColor("#5cb85c")) # Green
                elif req['status'] == 'Rejected':
                    status_item.setForeground(QColor("#333")) # Dark gray
                self.requests_table.setItem(row, 5, status_item)
                
                # Format date
                date_obj = datetime.fromisoformat(req['request_date'])
                self.requests_table.setItem(row, 6, QTableWidgetItem(date_obj.strftime("%Y-%m-%d %H:%M")))
            
            self.requests_table.sortItems(6, Qt.SortOrder.DescendingOrder) # Sort by date
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load material requests: {e}")
        
        # Clear details
        self.clear_request_details()

    def clear_request_details(self):
        """Clears the request details view."""
        self.request_details_label.setText("Select a request to see details.")
        self.request_line_items_table.setRowCount(0)
        self.approve_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        self.receive_stock_button.setEnabled(False)
        self.delete_request_button.setEnabled(False)

    def on_request_selected(self):
        """Loads line items when a request is selected."""
        selected_rows = self.requests_table.selectionModel().selectedRows()
        if not selected_rows:
            self.clear_request_details()
            return
            
        selected_row = selected_rows[0].row()
        request_id = int(self.requests_table.item(selected_row, 0).text())
        status = self.requests_table.item(selected_row, 5).text()
        
        self.request_details_label.setText(f"<b>Line Items for Request #{request_id}</b>")
        
        try:
            line_items = database.get_request_line_items(request_id)
            self.request_line_items_table.setRowCount(len(line_items))
            for row, item in enumerate(line_items):
                self.request_line_items_table.setItem(row, 0, QTableWidgetItem(item['material_name']))
                self.request_line_items_table.setItem(row, 1, QTableWidgetItem(str(item['quantity_needed'])))
                self.request_line_items_table.setItem(row, 2, QTableWidgetItem(item['unit_of_measure'])) # <-- NEW
                self.request_line_items_table.setItem(row, 3, QTableWidgetItem(f"₱{item['cost']:.2f}"))
            
            # Enable buttons based on status
            self.approve_button.setEnabled(status == 'Pending')
            self.reject_button.setEnabled(status == 'Pending')
            self.receive_stock_button.setEnabled(status == 'Approved')
            self.delete_request_button.setEnabled(True) # Can always delete
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load line items: {e}")

    def update_request_status(self, new_status):
        """Handler for Approve/Reject buttons."""
        selected_rows = self.requests_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Request Selected", "Please select a request.")
            return
            
        selected_row = selected_rows[0].row()
        request_id = int(self.requests_table.item(selected_row, 0).text())
        
        try:
            database.update_request_status(request_id, new_status)
            QMessageBox.information(self, "Success", f"Request #{request_id} has been {new_status}.")
            self.load_material_requests() # Refresh list
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update status: {e}")
            
    def delete_request(self):
        """Handler for 'Delete Request' button."""
        selected_rows = self.requests_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Request Selected", "Please select a request.")
            return
            
        selected_row = selected_rows[0].row()
        request_id = int(self.requests_table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to permanently delete Request #{request_id}?\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                database.delete_material_request(request_id)
                QMessageBox.information(self, "Success", f"Request #{request_id} has been deleted.")
                self.load_material_requests() # Refresh list
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete request: {e}")
                
    def receive_stock_and_complete(self):
        """Handler for 'Receive Stock' button."""
        selected_rows = self.requests_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Request Selected", "Please select a request.")
            return
            
        selected_row = selected_rows[0].row()
        request_id = int(self.requests_table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(
            self, "Confirm Stock Receipt",
            f"Are you sure you want to receive stock for Request #{request_id}?\n\n"
            "This will add all materials from this order to your inventory and mark the request as 'Completed'.\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                database.receive_material_request_stock(request_id)
                QMessageBox.information(self, "Success", 
                    f"Request #{request_id} is complete and stock has been added to inventory.")
                self.load_material_requests() # Refresh list
                self.load_materials_data() # Refresh materials (stock has changed)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not receive stock: {e}")
            
    # --- Tab 10: KPI Reports (Process 6) --- (NOW COMBINED)
    
    def create_forecast_kpi_tab(self):
        """Creates the combined 'Forecast & KPI Reports' tab UI."""
        widget = QWidget()
        # Main layout is side-by-side
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Left Side: Generate Forecast ---
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_layout.setSpacing(20)

        form_group = QGroupBox("Generate New Forecast (5)")
        form_group.setObjectName("FormGroup")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        
        self.forecast_product_combo = QComboBox()
        
        # --- UPDATED: Removed Target Year Spinbox ---
        # self.forecast_year_spinbox = QSpinBox()
        # self.forecast_year_spinbox.setMinimum(datetime.now().year)
        # self.forecast_year_spinbox.setMaximum(2050)
        # self.forecast_year_spinbox.setValue(datetime.now().year + 1)
        # --- END UPDATE ---
        
        self.forecast_increase_spinbox = QSpinBox()
        self.forecast_increase_spinbox.setMinimum(0)
        self.forecast_increase_spinbox.setMaximum(500)
        self.forecast_increase_spinbox.setValue(10)
        self.forecast_increase_spinbox.setSuffix(" %")

        self.generate_forecast_button = QPushButton("Generate and Save Forecast")
        self.generate_forecast_button.clicked.connect(self.run_forecast)
        
        form_layout.addRow("Product to Forecast:", self.forecast_product_combo)
        # --- UPDATED: Removed Target Year row ---
        # form_layout.addRow("Target Year:", self.forecast_year_spinbox)
        # --- END UPDATE ---
        form_layout.addRow("Target % Increase:", self.forecast_increase_spinbox)
        form_layout.addRow(self.generate_forecast_button)
        
        left_layout.addWidget(form_group)
        
        # --- NEW: Plot on left side ---
        plot_group = QGroupBox("Forecast Visualization")
        plot_layout = QVBoxLayout(plot_group)
        self.forecast_plot_canvas = reporting.MatplotlibCanvas(self)
        plot_layout.addWidget(self.forecast_plot_canvas)
        left_layout.addWidget(plot_group)
        # --- END NEW ---
        
        left_layout.addStretch()
        
        main_layout.addLayout(left_layout, 1) # Add left layout (1/3 width)
        
        # --- Right Side: KPI Reports (UPDATED WITH NESTED TABS) ---
        right_layout = QVBoxLayout()
        
        # --- Filters (Product filter REMOVED) ---
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("<b>KPI Report Filters (6)</b>"))
        
        filter_layout.addWidget(QLabel("Year:"))
        self.kpi_year_spinbox = QSpinBox(minimum=2020, maximum=2050)
        self.kpi_year_spinbox.setValue(datetime.now().year)
        filter_layout.addWidget(self.kpi_year_spinbox)
        
        self.run_reports_button = QPushButton("Generate Reports")
        self.run_reports_button.clicked.connect(self.run_kpi_reports)
        filter_layout.addWidget(self.run_reports_button)
        filter_layout.addStretch()
        
        right_layout.addLayout(filter_layout)
        
        # --- NEW: Nested Tab Widget ---
        self.kpi_tabs = QTabWidget()
        self.kpi_tabs.setObjectName("KpiTabs")
        
        # --- Create Canvas for "All Types" tab ---
        self.plot_all_1 = reporting.MatplotlibCanvas(self) # Sales vs Target YOY
        self.plot_all_2 = reporting.MatplotlibCanvas(self) # Historical Sales Summary
        self.plot_all_3 = reporting.MatplotlibCanvas(self) # Forecast vs Actual
        # self.plot_all_4 = reporting.MatplotlibCanvas(self) # <-- REMOVED
        self.kpi_tabs.addTab(
            self.create_kpi_grid(self.plot_all_1, self.plot_all_2, self.plot_all_3), # <-- UPDATED
            "All Types"
        )
        
        # --- Create Canvas for "P.E." tab ---
        self.plot_pe_1 = reporting.MatplotlibCanvas(self)
        self.plot_pe_2 = reporting.MatplotlibCanvas(self)
        self.plot_pe_3 = reporting.MatplotlibCanvas(self)
        # self.plot_pe_4 = reporting.MatplotlibCanvas(self) # <-- REMOVED
        self.kpi_tabs.addTab(
            self.create_kpi_grid(self.plot_pe_1, self.plot_pe_2, self.plot_pe_3), # <-- UPDATED
            "P.E. Shoes"
        )
        
        # --- Create Canvas for "Slip-on" tab ---
        self.plot_slipon_1 = reporting.MatplotlibCanvas(self)
        self.plot_slipon_2 = reporting.MatplotlibCanvas(self)
        self.plot_slipon_3 = reporting.MatplotlibCanvas(self)
        # self.plot_slipon_4 = reporting.MatplotlibCanvas(self) # <-- REMOVED
        self.kpi_tabs.addTab(
            self.create_kpi_grid(self.plot_slipon_1, self.plot_slipon_2, self.plot_slipon_3), # <-- UPDATED
            "Slip-on Shoes"
        )
        
        right_layout.addWidget(self.kpi_tabs)
        # --- END NEW ---
        
        main_layout.addLayout(right_layout, 2) # Add right layout (2/3 width)

        return widget

    def create_kpi_grid(self, canvas1, canvas2, canvas3):
        """Helper function to create a 3-plot grid."""
        grid_widget = QWidget()
        layout = QVBoxLayout(grid_widget)
        
        # Top plot (full width)
        layout.addWidget(canvas1)
        
        # Bottom plots (side-by-side)
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(canvas2)
        bottom_layout.addWidget(canvas3)
        
        layout.addLayout(bottom_layout)
        
        return grid_widget

    def run_kpi_reports(self):
        """Fetches all data and generates all 12 KPI reports."""
            
        year_filter = self.kpi_year_spinbox.value()
        
        try:
            # Fetch all data (only needs to happen once)
            past_sales_df = database.get_sales_history(is_historical_csv=True)
            current_sales_df = database.get_sales_history(is_historical_csv=False)
            targets_df = database.get_production_targets()
            predictions_df = database.get_predictions()

            # --- 1. Generate Reports for "All Types" ---
            self.generate_report_set(
                "All", year_filter,
                past_sales_df, current_sales_df, targets_df, predictions_df,
                self.plot_all_1, self.plot_all_2, self.plot_all_3 # <-- UPDATED
            )
            
            # --- 2. Generate Reports for "P.E." ---
            self.generate_report_set(
                "P.E.", year_filter,
                past_sales_df, current_sales_df, targets_df, predictions_df,
                self.plot_pe_1, self.plot_pe_2, self.plot_pe_3 # <-- UPDATED
            )
            
            # --- 3. Generate Reports for "Slip-on" ---
            self.generate_report_set(
                "Slip-on", year_filter,
                past_sales_df, current_sales_df, targets_df, predictions_df,
                self.plot_slipon_1, self.plot_slipon_2, self.plot_slipon_3 # <-- UPDATED
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Could not generate reports: {e}")

    def generate_report_set(self, category_filter, year_filter, 
                            past_sales_df, current_sales_df, targets_df, predictions_df,
                            canvas1, canvas2, canvas3):
        """Helper to run the 3 plotting functions for a specific category."""
        
        # --- Generate Plot 1: Sales vs Target YOY ---
        reporting.plot_sales_vs_target_yoy(
            canvas1.axes,
            past_sales_df,
            current_sales_df,
            targets_df,
            category_filter, # <-- Pass category filter
            year_filter
        )
        canvas1.draw()
        
        # --- Generate Plot 2: Historical Sales Summary ---
        reporting.plot_historical_sales_summary(
            canvas2.axes,
            past_sales_df,
            category_filter # <-- Pass category filter
        )
        canvas2.draw()
        
        # --- Generate Plot 3: Forecast vs Actual ---
        reporting.plot_forecast_vs_actual_admin(
            canvas3.axes,
            predictions_df,
            current_sales_df,
            category_filter, # <-- Pass category filter
            year_filter
        )
        canvas3.draw()

        # --- Generate Plot 4: Top Selling (Current) --- (REMOVED)
        
    # --- Styling ---
    def load_styles(self):
        """Loads the CSS stylesheet for the application."""
        stylesheet = """
        QMainWindow {
            background-color: #f0f2ff;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QTabWidget#MainTabs::pane {
            border: 1px solid #c5c5c5;
            border-top: 0px;
            background-color: #ffffff;
        }
        QTabWidget#MainTabs::tab-bar {
            alignment: left;
        }
        QTabBar::tab {
            background: #e4e6eb;
            border: 1px solid #c5c5c5;
            border-bottom: 0px;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            min-width: 80px; /* Give tabs more space */
        }
        QTabBar::tab:selected {
            background: #ffffff;
            border-bottom: 1px solid #ffffff;
        }
        QTabBar::tab:!selected:hover {
            background: #f0f2f5;
        }
        
        QWidget {
            font-size: 10pt;
        }
        
        /* Form & GroupBox Styles */
        QGroupBox, QWidget#FormGroup {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px; /* Reduced padding */
            margin-top: 10px;
        }
        QGroupBox::title, QLabel#FormTitle {
            font-size: 14pt;
            font-weight: bold;
            color: #1a237e;
            padding-bottom: 10px;
        }
        QLabel#InfoText {
            font-size: 9pt;
            color: #555;
            font-style: italic;
        }
        QLabel#TotalCostLabel {
            font-weight: bold;
            color: #004d40; /* Dark Teal */
            padding-top: 5px;
            font-size: 11pt;
        }
        
        QLineEdit, QSpinBox, QComboBox, QCalendarWidget {
            padding: 8px;
            border: 1px solid #c5c5c5;
            border-radius: 4px;
            font-size: 10pt;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border: 1px solid #0078d4;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            width: 20px;
        }
        
        /* Table Styles */
        QTableWidget {
            border: 1px solid #e0e0e0;
            gridline-color: #f0f0f0;
            font-size: 10pt;
        }
        QHeaderView::section {
            background-color: #f9f9f9;
            padding: 8px;
            border: 1px solid #e0e0e0;
            font-weight: bold;
        }
        QTableWidget::item {
            padding: 8px;
        }
        QTableWidget::item:selected {
            background-color: #e6f7ff;
            color: #000;
        }
        
        /* Button Styles */
        QPushButton {
            background-color: #0078d4;
            color: white;
            font-weight: bold;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            font-size: 10pt;
            min-height: 20px;
        }
        QPushButton:hover {
            background-color: #005a9e;
        }
        QPushButton:pressed {
            background-color: #004578;
        }
        QPushButton:disabled {
            background-color: #c5c5c5;
        }
        QPushButton#DeleteButton {
            background-color: #d93025; /* Red */
        }
        QPushButton#DeleteButton:hover {
            background-color: #a52714; /* Darker Red */
        }
        QPushButton#SendButton {
            background-color: #5cb85c; /* Green */
        }
        QPushButton#SendButton:hover {
            background-color: #449d44; /* Darker Green */
        }
        
        /* Welcome Tab Styles */
        QLabel#WelcomeTitle {
            font-size: 24pt;
            font-weight: bold;
            color: #333;
        }
        QLabel#WelcomeInfo {
            font-size: 12pt;
            color: #555;
            background-color: #f3e5f5; /* Light purple */
            border: 1px solid #ce93d8; /* Purple border */
            border-radius: 8px;
            padding: 20px;
        }
        QPushButton#LogoutButton {
            font-size: 10pt;
            font-weight: normal;
            background-color: #f0f2ff;
            color: #d93025;
            border: 1px solid #d93025;
            padding: 8px 15px;
        }
        QPushButton#LogoutButton:hover {
            background-color: #faeaea;
        }
        
        /* Style for the nested KPI tabs */
        QTabWidget#KpiTabs::pane {
            border: none;
        }
        QTabWidget#KpiTabs::tab-bar {
            alignment: center;
        }
        QTabWidget#KpiTabs QTabBar::tab {
            background: #f9f9f9;
            border: 1px solid #e0e0e0;
            padding: 8px 15px;
            font-size: 9pt;
            font-weight: bold;
            color: #555;
            min-width: 100px;
        }
        QTabWidget#KpiTabs QTabBar::tab:selected {
            background: #e6f7ff;
            color: #005a9e;
            border-bottom: 1px solid #e6f7ff;
        }
        QTabWidget#KpiTabs QTabBar::tab:!selected:hover {
            background: #f0f2f5;
        }
        """
        self.setStyleSheet(stylesheet)

if __name__ == '__main__':
    # This part is just for testing this window directly
    
    # --- THIS LINE WAS THE BUG AND HAS BEEN REMOVED ---
    # app = QApplication(sys.argv) 
    # --- END FIX ---
    
    # Mock a MainApplication class for the signal
    class MockApp(QApplication):
        logged_out = Signal()
        def __init__(self, argv):
            super().__init__(argv)
            # We need to initialize the database for the mock app to work
            try:
                database.init_db()
                # We need to import data for the app to work
                database.import_sales_from_csv("historical_sales.csv") # Assumes this file exists
            except Exception as e:
                print(f"Warning: Could not init/load mock data: {e}")
                
            self.main_win = AdminDashboard(1, "TestAdmin")
            self.main_win.logged_out.connect(self.on_logout)
            self.main_win.show()
            
        def on_logout(self):
            self.main_win.close()
            msg = QMessageBox()
            msg.setText("Logged out!")
            msg.exec()
            self.quit()

    app = MockApp(sys.argv) # This is now the ONLY QApplication instance
    sys.exit(app.exec())