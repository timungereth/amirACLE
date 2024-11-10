@echo off
REM D:\Software\GitHub\AmirACLE\button_menu_app\build_installer.bat

REM Set working directory
cd /d "%~dp0"

echo Building ButtonMenu Installer...
echo Working Directory: %CD%

REM Clean previous builds
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "installer" rmdir /s /q installer

REM Create executable
pyinstaller --clean ^
    --windowed ^
    --onefile ^
    --name ButtonMenu ^
    --add-data "README.md;." ^
    --hidden-import win32gui ^
    --hidden-import win32con ^
    --hidden-import win32api ^
    --hidden-import pynput.keyboard._win32 ^
    --hidden-import pynput.mouse._win32 ^
    "button_menu_app/button_menu.py"

REM Create installer directory
mkdir installer
copy dist\ButtonMenu.exe installer\
copy README.md installer\

REM Create launcher script in installer
echo @echo off > installer\Launch_ButtonMenu.bat
echo start ButtonMenu.exe >> installer\Launch_ButtonMenu.bat

REM Create autostart script in installer
echo @echo off > installer\Setup_Autostart.bat
echo echo Creating autostart entry... >> installer\Setup_Autostart.bat
echo mkdir "%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\Startup" 2^>nul >> installer\Setup_Autostart.bat
echo copy "ButtonMenu.exe" "%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\Startup\" >> installer\Setup_Autostart.bat
echo echo Autostart setup complete! >> installer\Setup_Autostart.bat
echo pause >> installer\Setup_Autostart.bat

REM Create ZIP file
powershell Compress-Archive -Path installer\* -DestinationPath ButtonMenu_Install.zip -Force

echo.
echo Build complete! 
echo Created files:
echo - installer\ButtonMenu.exe
echo - ButtonMenu_Install.zip
echo.
pause