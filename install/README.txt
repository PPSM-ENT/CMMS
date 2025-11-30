================================================================================
                    CMMS - Computerized Maintenance Management System
                              Installation Guide for Windows 11
================================================================================

PREREQUISITES
-------------
The installer will automatically download and install missing prerequisites:

1. Python 3.12 (auto-installed if missing)
2. Node.js 20 LTS (auto-installed if missing)

If you prefer to install them manually:
- Python: https://www.python.org/downloads/ (check "Add Python to PATH")
- Node.js: https://nodejs.org/ (LTS version)


INSTALLATION
------------
1. Copy the entire CMMS folder to your laptop (USB drive, network, etc.)

2. Double-click INSTALL.bat in the install folder
   - This will automatically request Administrator privileges
   - If Python or Node.js are missing, you'll be prompted to install them

   Alternative method (PowerShell):
   - Open PowerShell as Administrator (Win+X -> Terminal Admin)
   - Navigate to: cd "C:\path\to\CMMS\install"
   - Run: Set-ExecutionPolicy Bypass -Scope Process -Force; .\install.ps1

   Custom install location:
   - .\install.ps1 -InstallPath "D:\MyApps\CMMS"

3. Wait for installation to complete (5-15 minutes depending on internet speed)

4. If prerequisites were installed, you may need to restart and run installer again


STARTING CMMS
-------------
Option 1: Double-click "Start CMMS" shortcut on your Desktop

Option 2: Run from PowerShell:
   cd C:\CMMS
   .\start.ps1

Option 3: Double-click start.bat in the CMMS folder

The application will open in your browser automatically at:
   http://localhost:5173


STOPPING CMMS
-------------
Option 1: Double-click "Stop CMMS" shortcut on your Desktop

Option 2: Run from PowerShell:
   cd C:\CMMS
   .\stop.ps1

Option 3: Close both PowerShell windows (backend and frontend)


DEFAULT LOGIN
-------------
Email: admin@example.com
Password: admin123

IMPORTANT: Change this password after first login!


FOLDER STRUCTURE
----------------
C:\CMMS\
  ├── backend\           # Python FastAPI backend
  │   ├── app\           # Application code
  │   ├── venv\          # Python virtual environment
  │   └── .env           # Configuration file
  ├── frontend\          # React frontend
  │   ├── src\           # Source code
  │   ├── dist\          # Production build
  │   └── node_modules\  # Node.js packages
  ├── data\              # Database and uploads
  ├── start.ps1          # Start script
  ├── stop.ps1           # Stop script
  └── README.txt         # This file


CONFIGURATION
-------------
Backend configuration is stored in: C:\CMMS\backend\.env

Key settings:
- SECRET_KEY: Security key (auto-generated)
- DATABASE_URL: Database connection string
- ACCESS_TOKEN_EXPIRE_MINUTES: Session timeout (default: 480 = 8 hours)


TROUBLESHOOTING
---------------

Problem: "python is not recognized"
Solution: Reinstall Python and check "Add Python to PATH"

Problem: "npm is not recognized"
Solution: Reinstall Node.js and restart your terminal

Problem: Port 8000 or 5173 already in use
Solution: Run stop.ps1 or restart your computer

Problem: "Access denied" during installation
Solution: Run PowerShell as Administrator

Problem: Frontend shows "Cannot connect to backend"
Solution:
1. Check if backend window shows errors
2. Ensure port 8000 is not blocked by firewall
3. Try: http://localhost:8000/docs to test API

Problem: Database errors
Solution:
1. Delete C:\CMMS\data\cmms.db
2. Restart the application (database will be recreated)


BACKUP
------
To backup your data, copy the following:
- C:\CMMS\data\cmms.db (database)
- C:\CMMS\backend\.env (configuration)


UPDATES
-------
To update CMMS:
1. Stop CMMS (run stop.ps1)
2. Copy new files over existing installation
3. Run: cd C:\CMMS\backend && .\venv\Scripts\pip.exe install -r requirements.txt
4. Run: cd C:\CMMS\frontend && npm install
5. Start CMMS (run start.ps1)


SUPPORT
-------
For issues and feature requests, contact your system administrator.


================================================================================
