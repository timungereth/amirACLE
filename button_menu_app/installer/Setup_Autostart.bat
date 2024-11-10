@echo off 
echo Creating autostart entry... 
mkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup" 2>nul 
copy "ButtonMenu.exe" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\" 
echo Autostart setup complete! 
pause 
