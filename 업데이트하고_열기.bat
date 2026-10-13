@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 새 영상을 찾는 중... (몇 분 걸려요)
py -3.12 build_site.py --notify
start "" "%~dp0web\index.html"
pause
