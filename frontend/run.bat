@echo off
call conda activate "D:\WorkPace\Project\API-Testing\.conda"
python manage.py runserver localhost:8001
pause
