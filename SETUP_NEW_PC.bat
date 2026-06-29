@echo off
cd /d "%~dp0"
title Alpha1 WhatsApp - New PC Setup
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0SETUP_NEW_PC.ps1"
exit /b %ERRORLEVEL%
