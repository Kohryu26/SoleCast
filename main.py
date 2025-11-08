import sys
import matplotlib
# The backend is now set in reporting.py, so this file is clean.

from PySide6.QtWidgets import QApplication
from login_window import LoginWindow
from admin_dashboard import AdminDashboard
from employee_dashboard import EmployeeDashboard

class MainApplication(QApplication):
    """Main application class to manage windows."""
    def __init__(self, argv):
        super().__init__(argv)
        self.login_window = LoginWindow(self)
        self.dashboard = None

    def run(self):
        """Starts the application."""
        self.login_window.show()
        sys.exit(self.exec())

    def show_dashboard(self, user_id, username, role):
        """Hides the login window and shows the appropriate dashboard."""
        if self.dashboard:
            self.dashboard.close()
            
        try:
            if role == 'Admin':
                self.dashboard = AdminDashboard(user_id, username)
                self.dashboard.logged_out.connect(self.on_logout)
                self.dashboard.show()
                self.login_window.hide()
            elif role == 'Employee':
                self.dashboard = EmployeeDashboard(user_id, username)
                self.dashboard.logged_out.connect(self.on_logout)
                self.dashboard.show()
                self.login_window.hide()
            else:
                self.login_window.show_message("Login Error", "Unknown user role.")
                
        except Exception as e:
            print(f"Error loading dashboard: {e}")
            self.login_window.show_message("Dashboard Error", f"Could not load dashboard: {e}")
            # Show login window again if dashboard fails
            self.login_window.show()

    def on_logout(self):
        """Handles the logout signal from a dashboard."""
        if self.dashboard:
            self.dashboard.close()
            self.dashboard = None
            
        # --- THIS IS THE CORRECTED LOGIC ---
        self.login_window.clear_password()
        self.login_window.show()
        # --- END OF CORRECTED LOGIC ---

def main():
    # Set a consistent application name
    QApplication.setApplicationName("SoleCast")
    QApplication.setOrganizationName("SoleCast")
    
    app = MainApplication(sys.argv)
    app.run()

if __name__ == '__main__':
    main()