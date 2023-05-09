@echo off
cd /d %~dp0
if not exist env\Scripts\activate.bat (
    py -m venv env
)
call env\Scripts\activate.bat
set FLASK_APP=app
flask run