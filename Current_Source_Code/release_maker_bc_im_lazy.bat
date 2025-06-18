@echo off
setlocal enabledelayedexpansion

set NAME=ManualResizer
set ENTRY=__main__.pyw
set ICON=mewsiepto.ico
set DISTFOLDER=dist
set PICKFOLDER_SCRIPT=pick_folder.ps1

:: Clean old builds
rmdir /s /q build
rmdir /s /q %DISTFOLDER%
del /q %NAME%.spec

:: Build EXE
pyinstaller --noconsole --onefile --icon=%ICON% --name=%NAME% %ENTRY% --clean --distpath %DISTFOLDER% --add-data "manual.md;."

:: Ask user to pick release folder
for /f "usebackq tokens=*" %%i in (`powershell -noprofile -executionpolicy bypass -file "%PICKFOLDER_SCRIPT%"`) do set "RELEASEFOLDER=%%i"

:: If no folder picked, abort
if "%RELEASEFOLDER%"=="" (
    echo No folder selected. Aborting move.
    pause
    exit /b
)

:: Move the built exe to the selected folder
if not exist "%RELEASEFOLDER%" mkdir "%RELEASEFOLDER%"
move /Y ".\%DISTFOLDER%\%NAME%.exe" "%RELEASEFOLDER%\%NAME%.exe"

echo.
echo Done! Your EXE is now here:
echo %RELEASEFOLDER%\%NAME%.exe
pause
