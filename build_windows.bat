@echo off
setlocal enabledelayedexpansion

REM Build + optional code-sign + package script for MigrationDashboard (Windows)
REM Usage examples:
REM   build_windows.bat
REM   set APP_NAME=MigrationDashboard && build_windows.bat
REM   set SIGN_APP=1 && set SIGNTOOL_CERT_SUBJECT=Your Company, Inc. && build_windows.bat

if "%APP_NAME%"=="" set APP_NAME=MigrationDashboard
if "%ENTRYPOINT%"=="" set ENTRYPOINT=run_dashboard.py
if "%SIGN_APP%"=="" set SIGN_APP=0
if "%SIGNTOOL_TIMESTAMP%"=="" set SIGNTOOL_TIMESTAMP=http://timestamp.digicert.com

set DIST_DIR=dist\%APP_NAME%
set RELEASE_DIR=release\%APP_NAME%-win

cd /d "%~dp0"

if not exist "%ENTRYPOINT%" (
  echo ❌ Entrypoint not found: %ENTRYPOINT%
  exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
  echo ❌ Python is required but was not found in PATH
  exit /b 1
)

if not exist .venv (
  echo 📦 Creating local virtual environment (.venv)...
  python -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo 🧹 Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"

echo 🏗️ Building portable onedir bundle with PyInstaller...
pyinstaller "%ENTRYPOINT%" ^
  --name "%APP_NAME%" ^
  --onedir ^
  --clean ^
  --noconfirm ^
  --add-data "app.py;." ^
  --add-data "pages;pages" ^
  --add-data "ui;ui" ^
  --add-data "core;core" ^
  --add-data "data_loaders;data_loaders" ^
  --add-data "models;models" ^
  --add-data "analytics;analytics" ^
  --add-data "components;components" ^
  --add-data "utils;utils" ^
  --add-data "export;export"

if "%SIGN_APP%"=="1" (
  where signtool >nul 2>nul
  if errorlevel 1 (
    echo ❌ SIGN_APP=1 but signtool was not found in PATH
    exit /b 1
  )

  echo 🔏 Signing executable...
  if not "%SIGNTOOL_CERT_SUBJECT%"=="" (
    signtool sign /fd SHA256 /tr "%SIGNTOOL_TIMESTAMP%" /td SHA256 /n "%SIGNTOOL_CERT_SUBJECT%" "%DIST_DIR%\%APP_NAME%.exe"
  ) else (
    signtool sign /fd SHA256 /tr "%SIGNTOOL_TIMESTAMP%" /td SHA256 /a "%DIST_DIR%\%APP_NAME%.exe"
  )

  signtool verify /pa /v "%DIST_DIR%\%APP_NAME%.exe"
)

echo 📁 Preparing USB-portable release directory...
mkdir "%RELEASE_DIR%"
xcopy /E /I /Y "%DIST_DIR%" "%RELEASE_DIR%" >nul

powershell -NoProfile -Command "Compress-Archive -Path '%RELEASE_DIR%\*' -DestinationPath 'release\%APP_NAME%-win-portable.zip' -Force" >nul 2>nul

echo 🎉 Done. Artifacts:
echo    - %DIST_DIR%
echo    - %RELEASE_DIR%
echo    - release\%APP_NAME%-win-portable.zip

endlocal
