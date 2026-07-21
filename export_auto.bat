@echo off
cd /d C:\Users\user\Documents\eqdom-from-scratch
call venv\Scripts\activate.bat
python manage.py export_powerbi
python manage.py calculer_stats_gold