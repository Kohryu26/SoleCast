import sys
import bcrypt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, 
    QPushButton, QLabel, QMessageBox, QFormLayout, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import database

class LoginWindow(QWidget):
    """
    Login window for the SoleCast application.
    Emits a signal with user_id, username, and role upon successful login.
    """
    
    # Define signals
    # login_successful = Signal(int, str, str) # No longer needed, app handles this

    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance  # Store the main application instance
        self.init_ui()
        self.load_styles()

    def init_ui(self):
        """Initializes the UI components."""
        self.setWindowTitle("SoleCast - Login")
        self.setGeometry(400, 400, 400, 350)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- Title ---
        title_label = QLabel("SoleCast LogIn")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # --- Form Layout for Inputs ---
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        # Handle Enter key press
        self.password_input.returnPressed.connect(self.handle_login)

        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        
        main_layout.addLayout(form_layout)

        # --- Login Button ---
        self.login_button = QPushButton("Log In")
        self.login_button.setObjectName("LoginButton")
        self.login_button.clicked.connect(self.handle_login)
        main_layout.addWidget(self.login_button)
        
        # --- Forgot Password Button ---
        self.forgot_password_button = QPushButton("Forgot Password?")
        self.forgot_password_button.setObjectName("ForgotPasswordButton")
        self.forgot_password_button.clicked.connect(self.handle_forgot_password)
        main_layout.addWidget(self.forgot_password_button)
        
        main_layout.addStretch() # Pushes content up

    def handle_login(self):
        """Handles the login button click event."""
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            self.show_message("Login Error", "Username and password are required.")
            return

        try:
            # --- THIS IS THE CORRECTED LOGIC ---
            user_data = database.get_user(username)
            
            if user_data:
                # Check the password
                hashed_password = user_data['password_hash']
                if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                    # Passwords match!
                    # self.show_message("Login Success", f"Welcome, {username}!")
                    
                    # Tell the main app to show the dashboard
                    self.app.show_dashboard(
                        user_data['user_id'], 
                        user_data['username'], 
                        user_data['role']
                    )
                else:
                    # Passwords do not match
                    self.show_message("Login Failed", "Invalid username or password.")
            else:
                # User not found
                self.show_message("Login Failed", "Invalid username or password.")
            # --- END OF CORRECTED LOGIC ---
                
        except Exception as e:
            print(f"Login error: {e}")
            self.show_message("Login Error", f"An error occurred: {e}")
            
    def handle_forgot_password(self):
        """Shows a help message for forgotten passwords."""
        self.show_message(
            "Forgot Password",
            "Please contact an Administrator to have your password reset."
        )

    def show_message(self, title, message):
        """Helper function to display a message box."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(
            QMessageBox.Icon.Information if "Success" in title else QMessageBox.Icon.Warning
        )
        msg_box.exec()
        
    def clear_password(self):
        """Clears the password field (called on logout)."""
        self.password_input.clear()

    def load_styles(self):
        """Loads the CSS stylesheet for the login window."""
        self.setStyleSheet("""
        QWidget {
            background-color: #f0f2ff;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QLabel#TitleLabel {
            font-size: 24pt;
            font-weight: bold;
            color: #1a237e; /* Dark Indigo */
        }
        QLineEdit {
            padding: 10px;
            font-size: 11pt;
            border: 1px solid #c5c5c5;
            border-radius: 5px;
            background-color: white;
        }
        QLineEdit:focus {
            border: 1px solid #0078d4;
        }
        QPushButton#LoginButton {
            background-color: #0078d4;
            color: white;
            font-weight: bold;
            font-size: 12pt;
            padding: 12px;
            border-radius: 5px;
            border: none;
        }
        QPushButton#LoginButton:hover {
            background-color: #005a9e;
        }
        QPushButton#LoginButton:pressed {
            background-color: #004578;
        }
        QPushButton#ForgotPasswordButton {
            background-color: transparent;
            color: #0078d4;
            font-size: 9pt;
            border: none;
            text-decoration: underline;
        }
        QPushButton#ForgotPasswordButton:hover {
            color: #005a9e;
        }
        """)

if __name__ == '__main__':
    # This part is just for testing this window directly
    
    # Mock a MainApplication class for testing
    class MockApp(QApplication):
        def __init__(self, argv):
            super().__init__(argv)
            self.login_window = LoginWindow(self)
            self.login_window.show()
            
        def show_dashboard(self, user_id, username, role):
            print(f"Login successful for {username} (ID: {user_id}, Role: {role})")
            msg = QMessageBox()
            msg.setText(f"Login successful! Welcome, {username} ({role}).")
            msg.exec()
            self.login_window.hide()
            
    app = MockApp(sys.argv)
    sys.exit(app.exec())