@echo off
REM Builds SciCalc.exe (run this on Windows with Python 3.9+ installed from python.org)
python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconsole --onefile --name SciCalc --icon scicalc.ico --add-data "scicalc.ico;." scicalc.py
echo.
echo Done. Your program is: dist\SciCalc.exe
pause
