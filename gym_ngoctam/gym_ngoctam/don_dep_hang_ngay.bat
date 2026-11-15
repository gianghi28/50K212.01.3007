@echo off
REM Chay don dep hoi vien (UC02.3 - TH2). Task Scheduler goi file nay luc 00:00 moi ngay.
cd /d "%~dp0"
if not exist logs mkdir logs
python manage.py don_dep_hoi_vien >> logs\don_dep_console.txt 2>&1
