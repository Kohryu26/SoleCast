import sys
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QComboBox,
    QLabel, QPushButton, QFormLayout, QHBoxLayout, QMessageBox,
    QGroupBox, QTextEdit, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor

import database
import reporting
# import forecasting_model # No longer needed, forecast is admin-only
from datetime import datetime

# --- Print Preview Dialog ---
class PrintPreviewDialog(QDialog):
    """A dialog to show a printable text preview of the request."""
    def __init__(self, report_html, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Print Request Preview")
        self.setGeometry(200, 200, 500, 600)
        
        layout = QVBoxLayout(self)
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setHtml(report_html) # Use HTML for basic formatting
        layout.addWidget(self.text_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

class EmployeeDashboard(QMainWindow):
    logged_out = Signal()

    def __init__(self, user_id, username):
        super().__init__()
        self.user_id = user_id
        self.username = username
        
        self.setWindowTitle(f"SoleCast Employee Dashboard - Welcome, {self.username}")
        self.setGeometry(100, 100, 1200, 800)
        
        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        self.setCentralWidget(self.tabs)
        
        # Cache for product list
        self.product_list = []
        
        # Cache for the current material request
        self.current_line_items = []
        self.current_total_cost = 0.0
        
        self.setup_tabs()
        self.load_styles()
        
    def setup_tabs(self):
        """Initializes all the tabs for the dashboard."""
        self.tabs.addTab(self.create_welcome_tab(), "Welcome")
        # "Handle Forecasts" tab is removed, now admin-only
        self.tabs.addTab(self.create_costing_tab(), "Material Costing & Request")
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        # Load data for the first tab (Welcome)
        self.load_request_summary()
        
    def on_tab_changed(self, index):
        """Loads data for the currently selected tab."""
        tab_title = self.tabs.tabText(index)
        
        # Always refresh product list when tabs change
        self.refresh_product_list()
        
        if "Welcome" in tab_title:
            self.load_request_summary()
        elif "Material Costing" in tab_title:
            # Load products for costing dropdown
            self.cost_product_combo.clear()
            self.cost_product_combo.addItems(self.product_list)
            # Auto-load materials data
            self.load_materials_data()

    def refresh_product_list(self):
        """Gets a list of unique product names from sales history."""
        try:
            df = database.get_sales_history()
            if df.empty:
                self.product_list = ["(No products found)"]
                return
            self.product_list = sorted(list(df['product_name'].unique()))
        except Exception as e:
            print(f"Error getting product list: {e}")
            self.product_list = ["(Error)"]

    # --- Tab 1: Welcome (UPDATED) ---
    def create_welcome_tab(self):
        """Creates the welcome tab with general info and request summary."""
        widget = QWidget()
        main_layout = QHBoxLayout(widget) # Main layout is Horizontal
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # --- Left Side: Welcome Info ---
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        title = QLabel("SoleCast: Employee Dashboard")
        title.setObjectName("WelcomeTitle")
        
        info = QLabel(f"""
        Welcome, <b>{self.username}</b>.
        
        Please use the <b>'Material Costing & Request'</b> tab to:
        <ul>
            <li>Calculate material needs based on the Admin's BOM.</li>
            <li>Submit new material requests for approval.</li>
        </ul>
        You can see a summary of your submitted requests on this page.
        """)
        info.setObjectName("WelcomeInfo")
        info.setWordWrap(True)

        left_layout.addWidget(title)
        left_layout.addWidget(info)
        left_layout.addStretch() # Pushes the button to the bottom

        # Logout Button
        self.logout_button = QPushButton("Log Out")
        self.logout_button.setObjectName("LogoutButton")
        self.logout_button.clicked.connect(self.handle_logout)
        
        # Align button to the right
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.logout_button)
        left_layout.addLayout(button_layout)
        
        main_layout.addLayout(left_layout, 1) # Add left side (1/3 width)
        
        # --- Right Side: Request Summary ---
        right_group = QGroupBox("My Request Summary")
        right_layout = QVBoxLayout(right_group)
        
        # Refresh button for the summary table
        summary_header_layout = QHBoxLayout()
        summary_header_layout.addStretch()
        self.refresh_summary_button = QPushButton("Refresh Summary")
        self.refresh_summary_button.clicked.connect(self.load_request_summary)
        summary_header_layout.addWidget(self.refresh_summary_button)
        right_layout.addLayout(summary_header_layout)
        
        self.request_summary_table = QTableWidget()
        self.request_summary_table.setColumnCount(5)
        self.request_summary_table.setHorizontalHeaderLabels(
            ["Request ID", "Product", "Total Cost (₱)", "Status", "Date"]
        )
        self.request_summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.request_summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.request_summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        right_layout.addWidget(self.request_summary_table)
        
        main_layout.addWidget(right_group, 2) # Add right side (2/3 width)
        
        return widget

    def load_request_summary(self):
        """Loads the summary of material requests submitted by this employee."""
        try:
            requests = database.get_material_requests_by_employee(self.user_id)
            self.request_summary_table.setRowCount(len(requests))
            
            for row, req in enumerate(requests):
                self.request_summary_table.setItem(row, 0, QTableWidgetItem(str(req['request_id'])))
                self.request_summary_table.setItem(row, 1, QTableWidgetItem(req['product_name']))
                self.request_summary_table.setItem(row, 2, QTableWidgetItem(f"₱{req['total_cost']:.2f}"))
                
                status_item = QTableWidgetItem(req['status'])
                if req['status'] == 'Pending':
                    status_item.setForeground(QColor("#d9534f")) # Red
                elif req['status'] == 'Approved':
                    status_item.setForeground(QColor("#0275d8")) # Blue
                elif req['status'] == 'Completed':
                    status_item.setForeground(QColor("#5cb85c")) # Green
                elif req['status'] == 'Rejected':
                    status_item.setForeground(QColor("#333")) # Dark gray
                self.request_summary_table.setItem(row, 3, status_item)
                
                date_obj = datetime.fromisoformat(req['request_date'])
                self.request_summary_table.setItem(row, 4, QTableWidgetItem(date_obj.strftime("%Y-%m-%d %H:%M")))
            
            self.request_summary_table.sortItems(4, Qt.SortOrder.DescendingOrder) # Sort by date
            
        except Exception as e:
            print(f"Error loading request summary: {e}")
            QMessageBox.critical(self, "Error", f"Could not load request summary: {e}")

    def handle_logout(self):
        """Emits the logged_out signal."""
        self.logged_out.emit()

    # --- Tab 2: Material Costing (LAYOUT UPDATED) ---
    def create_costing_tab(self):
        """Creates the 'Material Costing & Request' tab UI."""
        widget = QWidget()
        # --- Main layout is now VERTICAL ---
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Top Section: Cost Calculator ---
        calc_group = QGroupBox("Cost Calculator")
        calc_layout = QFormLayout(calc_group)
        
        self.cost_product_combo = QComboBox()
        self.cost_quantity_spinbox = QSpinBox(minimum=1, maximum=10000)
        self.cost_quantity_spinbox.setValue(100)
        
        self.calculate_cost_button = QPushButton("Calculate Required Materials")
        self.calculate_cost_button.clicked.connect(self.calculate_material_cost)
        # --- THIS BUTTON IS ENABLED BY DEFAULT ---
        
        calc_layout.addRow("Product to Produce:", self.cost_product_combo)
        calc_layout.addRow("Number of Pairs:", self.cost_quantity_spinbox)
        calc_layout.addRow(self.calculate_cost_button)
        
        # Add calculator to the top of the main layout
        main_layout.addWidget(calc_group)
        
        # --- Bottom Section: Side-by-side tables ---
        bottom_layout = QHBoxLayout()
        
        # --- Bottom-Left: Current Inventory ---
        inventory_group = QGroupBox("Current Material Inventory")
        left_layout = QVBoxLayout(inventory_group) # New QVBoxLayout
        
        inv_header_layout = QHBoxLayout()
        inv_header_layout.addStretch()
        self.refresh_materials_button = QPushButton("Request Updated Inventory")
        self.refresh_materials_button.clicked.connect(self.load_materials_data)
        inv_header_layout.addWidget(self.refresh_materials_button)
        
        left_layout.addLayout(inv_header_layout)
        
        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(6)
        self.materials_table.setHorizontalHeaderLabels(["ID", "Name", "Current Stock", "Unit", "Price/Unit (₱)", "Product"])
        self.materials_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.materials_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.materials_table.setColumnWidth(1, 200)
        self.materials_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        left_layout.addWidget(self.materials_table)
        bottom_layout.addWidget(inventory_group, 2) # Add inventory to bottom layout (2/3 width)
        
        # --- Bottom-Right: Cost Breakdown ---
        breakdown_group = QGroupBox("Cost Breakdown & Request")
        breakdown_layout = QVBoxLayout(breakdown_group)
        
        self.cost_table = QTableWidget()
        self.cost_table.setColumnCount(6)
        self.cost_table.setHorizontalHeaderLabels(["Material", "Total Required", "In Stock", "Need to Order", "Unit", "Cost"])
        self.cost_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cost_table.setColumnWidth(0, 150)
        self.cost_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.total_cost_label = QLabel("Total Estimated Cost for New Materials: ₱0.00")
        self.total_cost_label.setObjectName("TotalCostLabel")
        
        # --- Button Layout ---
        button_layout = QHBoxLayout()
        
        self.complete_request_button = QPushButton("Complete & Clear")
        self.complete_request_button.clicked.connect(self.complete_and_clear_request)
        self.complete_request_button.setEnabled(False) 
        
        self.print_request_button = QPushButton("Print Request")
        self.print_request_button.clicked.connect(self.handle_print_request)
        self.print_request_button.setEnabled(False) 

        self.submit_request_button = QPushButton("Send Request to Admin") 
        self.submit_request_button.clicked.connect(self.submit_material_request)
        self.submit_request_button.setEnabled(False) 
        self.submit_request_button.setObjectName("SendButton") 
        
        button_layout.addWidget(self.complete_request_button)
        button_layout.addWidget(self.print_request_button)
        button_layout.addWidget(self.submit_request_button)
        
        breakdown_layout.addWidget(self.cost_table)
        breakdown_layout.addWidget(self.total_cost_label)
        breakdown_layout.addLayout(button_layout) 
        
        bottom_layout.addWidget(breakdown_group, 1) # Add breakdown to bottom layout (1/3 width)
        
        # Add the bottom layout to the main layout
        main_layout.addLayout(bottom_layout)

        return widget

    def load_materials_data(self):
        """
        Loads all material data from the database and populates
        the inventory table. This acts as the "Request Updated Inventory" button.
        """
        print("Loading materials data...")
        try:
            # self.all_materials_data = database.get_all_materials()
            all_materials = database.get_all_materials()
            self.materials_table.setRowCount(len(all_materials))
            
            for row, material in enumerate(all_materials):
                self.materials_table.setItem(row, 0, QTableWidgetItem(str(material['material_id'])))
                self.materials_table.setItem(row, 1, QTableWidgetItem(material['name']))
                self.materials_table.setItem(row, 2, QTableWidgetItem(str(material['stock'])))
                self.materials_table.setItem(row, 3, QTableWidgetItem(material['unit_of_measure']))
                self.materials_table.setItem(row, 4, QTableWidgetItem(f"{material['price']:.2f}"))
                self.materials_table.setItem(row, 5, QTableWidgetItem(material['product_association']))
            
            print("Material data refreshed.")
            
            # Clear the calculator if data is refreshed
            self.clear_cost_calculator()

        except Exception as e:
            print(f"Error loading materials: {e}")
            QMessageBox.critical(self, "Error", f"Could not load materials: {e}")
            
    def clear_cost_calculator(self):
        """Resets the cost breakdown table and caches."""
        self.cost_table.setRowCount(0)
        self.total_cost_label.setText("Total Estimated Cost for New Materials: ₱0.00")
        
        # Disable all action buttons
        self.submit_request_button.setEnabled(False)
        self.print_request_button.setEnabled(False)
        self.complete_request_button.setEnabled(False)
        
        self.current_line_items = []
        self.current_total_cost = 0.0

    def calculate_material_cost(self):
        """
        Calculates the cost of materials needed for a production run
        based on the Bill of Materials (BOM) from the database.
        """
        self.clear_cost_calculator() # Clear previous calculation
        
        selected_product = self.cost_product_combo.currentText()
        quantity_to_produce = self.cost_quantity_spinbox.value()
        
        if "(No products found)" in selected_product:
            QMessageBox.warning(self, "Error", "No products available to calculate.")
            return

        try:
            # Get the BOM for this product from the database
            bom_items = database.get_bom_for_product(selected_product)
            
            if not bom_items:
                QMessageBox.critical(self, "Error", 
                    f"No Bill of Materials (BOM) is defined for '{selected_product}'.\n"
                    "Please ask an Admin to set up the BOM."
                )
                return
                
            self.cost_table.setRowCount(len(bom_items))
            total_cost = 0.0
            line_items_cache = []
            
            for row, item in enumerate(bom_items):
                mat_name = item['name']
                required_per_unit = item['quantity_per_unit']
                in_stock = item['stock']
                price = item['price']
                unit = item['unit_of_measure']
                
                total_required = quantity_to_produce * required_per_unit
                need_to_order = max(0, total_required - in_stock)
                cost = need_to_order * price
                total_cost += cost
                
                # Populate table row
                self.cost_table.setItem(row, 0, QTableWidgetItem(mat_name))
                self.cost_table.setItem(row, 1, QTableWidgetItem(str(total_required)))
                self.cost_table.setItem(row, 2, QTableWidgetItem(str(in_stock)))
                self.cost_table.setItem(row, 3, QTableWidgetItem(str(need_to_order)))
                self.cost_table.setItem(row, 4, QTableWidgetItem(unit))
                self.cost_table.setItem(row, 5, QTableWidgetItem(f"₱{cost:,.2f}"))
                
                # Cache for submission
                line_items_cache.append({
                    "material_name": mat_name,
                    "quantity_needed": need_to_order,
                    "unit_of_measure": unit, # Added unit
                    "cost": cost
                })

            self.total_cost_label.setText(f"Total Estimated Cost for New Materials: ₱{total_cost:,.2f}")
            
            # Store results for submission
            self.current_line_items = line_items_cache
            self.current_total_cost = total_cost
            
            # Enable action buttons
            self.submit_request_button.setEnabled(True)
            self.print_request_button.setEnabled(True)
            self.complete_request_button.setEnabled(True)
            
        except Exception as e:
            print(f"Error in calculation: {e}")
            QMessageBox.critical(self, "Error", f"Could not calculate cost: {e}")

    def complete_and_clear_request(self):
        """'Completes' a request by saving it to a new 'completed' table and clearing."""
        if not self.current_line_items or not self.complete_request_button.isEnabled():
            QMessageBox.warning(self, "Error", "Please calculate a cost breakdown first.")
            return
            
        product_name = self.cost_product_combo.currentText()
        production_quantity = self.cost_quantity_spinbox.value()
        
        reply = QMessageBox.question(
            self, "Confirm Complete",
            f"Are you sure you want to mark this request as complete and clear the form?\n\n"
            f"Product: {product_name}\n"
            f"Total Cost: ₱{self.current_total_cost:.2f}\n\n"
            "This will be saved to your local 'Completed Orders' log.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
            
        try:
            # Use the NEW database function
            request_id = database.add_completed_material_order(
                employee_id=self.user_id,
                employee_name=self.username,
                product_name=product_name,
                production_quantity=production_quantity,
                total_cost=self.current_total_cost,
                line_items=self.current_line_items
            )
            QMessageBox.information(
                self, "Success", 
                f"Local Order #{request_id} has been saved and completed!"
            )
            # Clear calculator
            self.clear_cost_calculator()
            
        except Exception as e:
            print(f"Error completing request: {e}")
            QMessageBox.critical(self, "Error", f"Could not save completed order: {e}")

    def handle_print_request(self):
        """Generates an HTML report and shows it in a print preview dialog."""
        if not self.current_line_items or not self.print_request_button.isEnabled():
            QMessageBox.warning(self, "Error", "Please calculate a cost breakdown first.")
            return
            
        product_name = self.cost_product_combo.currentText()
        production_quantity = self.cost_quantity_spinbox.value()

        # Generate HTML for the report
        report_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; }}
                h1 {{ color: #1a237e; font-size: 16pt; }}
                h2 {{ color: #333; font-size: 12pt; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ccc; padding: 6px; text-align: left; }}
                th {{ background-color: #f4f4f4; }}
                .total {{ font-weight: bold; font-size: 11pt; color: #004d40; }}
            </style>
        </head>
        <body>
            <h1>Material Cost Request</h1>
            <p>Generated by: <b>{self.username}</b> on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            
            <h2>Summary</h2>
            <p>
                <b>Product to Produce:</b> {product_name}<br>
                <b>Number of Pairs:</b> {production_quantity}
            </p>
            
            <h2>Cost Breakdown (Materials to Order)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Material</th>
                        <th>Qty Needed</th>
                        <th>Unit</th>
                        <th>Cost</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Get BOM to fetch units (already in self.current_line_items)
        for item in self.current_line_items:
            if item['quantity_needed'] > 0:
                unit = item.get('unit_of_measure', 'pcs')
                report_html += f"""
                    <tr>
                        <td>{item['material_name']}</td>
                        <td>{item['quantity_needed']}</td>
                        <td>{unit}</td>
                        <td>₱{item['cost']:,.2f}</td>
                    </tr>
                """
        
        report_html += f"""
                </tbody>
            </table>
            <br>
            <p class="total">
                Total Estimated Cost for New Materials: ₱{self.current_total_cost:,.2f}
            </p>
        </body>
        </html>
        """
        
        # Show the dialog
        dialog = PrintPreviewDialog(report_html, self)
        dialog.exec()

    def submit_material_request(self):
        """
        Submits the calculated material request to the database
        for admin approval.
        """
        if not self.current_line_items or not self.submit_request_button.isEnabled():
            QMessageBox.warning(self, "Error", "Please calculate a cost breakdown first.")
            return
            
        product_name = self.cost_product_combo.currentText()
        production_quantity = self.cost_quantity_spinbox.value()
        
        reply = QMessageBox.question(
            self, "Confirm Request",
            f"Are you sure you want to submit a request for:\n\n"
            f"Product: {product_name}\n"
            f"Quantity: {production_quantity} pairs\n"
            f"Total Cost: ₱{self.current_total_cost:.2f}\n\n"
            "This will be sent to the Admin for approval.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
            
        try:
            request_id = database.submit_material_request(
                employee_id=self.user_id,
                employee_name=self.username,
                product_name=product_name,
                production_quantity=production_quantity,
                total_cost=self.current_total_cost,
                line_items=self.current_line_items
            )
            QMessageBox.information(
                self, "Success", 
                f"Material Request #{request_id} submitted successfully!"
            )
            # Clear calculator
            self.clear_cost_calculator()
            
        except Exception as e:
            print(f"Error submitting request: {e}")
            QMessageBox.critical(self, "Error", f"Could not submit request: {e}")

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
        QLabel#TotalCostLabel {
            font-size: 13pt;
            font-weight: bold;
            color: #004d40; /* Dark Teal */
            padding-top: 10px;
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
        }
        QPushButton:hover {
            background-color: #005a9e;
        }
        QPushButton:pressed {
            background-color: #004578;
        }
        
        /* Style for the "Send" button */
        QPushButton#SendButton {
            background-color: #5cb85c; /* Green */
            font-size: 11pt;
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
        """
        self.setStyleSheet(stylesheet)

if __name__ == '__main__':
    # This part is just for testing this window directly
    app = QApplication(sys.argv)
    
    # Mock a MainApplication class for the signal
    class MockApp(QApplication):
        logged_out = Signal()
        def __init__(self, argv):
            super().__init__(argv)
            self.main_win = EmployeeDashboard(2, "TestEmployee")
            self.main_win.logged_out.connect(self.on_logout)
            self.main_win.show()
            
        def on_logout(self):
            self.main_win.close()
            msg = QMessageBox()
            msg.setText("Logged out!")
            msg.exec()
            self.quit()

    app = MockApp(sys.argv)
    sys.exit(app.exec())