@echo off
title Cosmo Label Printer - EXE Builder
color 0A
cls

echo ============================================================
echo   COSMO HYDRAULIC INDUSTRIES - EXE Builder
echo   Ye script main.py ko single .exe file banayega
echo ============================================================
echo.

:: Check karo Python install hai ya nahi
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python nahi mila! 
    echo.
    echo Python install karo: https://www.python.org/downloads/
    echo Install karte waqt "Add Python to PATH" zaroor tick karna!
    echo.
    pause
    exit /b 1
)

echo [1/4] Python mila - checking libraries...
echo.

:: PyInstaller install karo agar nahi hai
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller install ho raha hai...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        color 0C
        echo [ERROR] PyInstaller install nahi hua. Internet check karo.
        pause
        exit /b 1
    )
)

:: Baaki required libraries install karo
echo [2/4] Required libraries check/install ho rahi hain...
pip install pillow qrcode[pil] python-barcode --quiet
echo     Pillow, qrcode, python-barcode - OK
echo.

:: Check karo main.py same folder mein hai
if not exist "main.py" (
    color 0C
    echo [ERROR] main.py is folder mein nahi mila!
    echo.
    echo Please BUILD_KARO.bat aur main.py ko SAME folder mein rakho.
    echo.
    pause
    exit /b 1
)

echo [3/4] Building EXE... (2-5 minute lag sakte hain, wait karo)
echo.

:: PyInstaller command - single file, no console window
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "CosmoLabelPrinter" ^
    --hidden-import="PIL._tkinter_finder" ^
    --hidden-import="PIL.Image" ^
    --hidden-import="PIL.ImageTk" ^
    --hidden-import="PIL.ImageDraw" ^
    --hidden-import="PIL.ImageFont" ^
    --hidden-import="qrcode" ^
    --hidden-import="qrcode.image.pil" ^
    --hidden-import="qrcode.constants" ^
    --hidden-import="barcode" ^
    --hidden-import="barcode.writer" ^
    --hidden-import="tkinter" ^
    --hidden-import="tkinter.ttk" ^
    --hidden-import="tkinter.messagebox" ^
    --hidden-import="tkinter.filedialog" ^
    --hidden-import="tkinter.simpledialog" ^
    --hidden-import="sqlite3" ^
    --hidden-import="hashlib" ^
    --hidden-import="threading" ^
    --collect-all="qrcode" ^
    --collect-all="barcode" ^
    main.py

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [ERROR] Build fail hua! Upar ka error message dekho.
    echo.
    echo Common fixes:
    echo   - Antivirus temporarily band karo
    echo   - Folder ka path simple rakho (C:\CosmoApp\)
    echo   - Spaces wale path mein problem hoti hai
    echo.
    pause
    exit /b 1
)

echo.
echo [4/4] Cleaning up temp files...
:: Temp files saaf karo
if exist "build" rmdir /s /q "build"
if exist "CosmoLabelPrinter.spec" del /q "CosmoLabelPrinter.spec"
echo.

color 0A
echo ============================================================
echo   BUILD SUCCESSFUL! EXE BAN GAYI!
echo ============================================================
echo.
echo   Location: dist\CosmoLabelPrinter.exe
echo.
echo   Ye ek SINGLE FILE hai - kisi bhi Windows laptop par
echo   seedha copy karke chalao, kuch install karne ki zaroorat nahi!
echo.
echo   NOTE: Pehli baar thoda slow open hoga (normal hai)
echo         Antivirus false alarm de sakta hai - allow kar dena
echo.

:: dist folder kholo automatically
explorer dist

pause