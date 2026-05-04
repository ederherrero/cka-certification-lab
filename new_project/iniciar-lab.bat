@echo off
cd /d "%~dp0"
echo Iniciando o CKA Lab...
vagrant up
echo.
echo Pronto! Acesse http://localhost:8080
pause
