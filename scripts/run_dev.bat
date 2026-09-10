@echo off
rem =====================================================================
rem  iBanking Tuition Payment - KHOI DONG 3 SERVICE NEN TANG
rem
rem  Dieu kien truoc khi chay:
rem    - Da tao 6 database va chay db\01, db\02, db\03 tren SQL Server
rem    - Da chay db\generate_password_hashes.py va UPDATE hash vao AuthDB
rem    - Da copy services\.env.example thanh services\.env va dien DB_PWD
rem    - Da cai thu vien: pip install -r services\requirements.txt
rem
rem  Kiem tra moi truong truoc (khuyen nghi): python scripts\check_env.py
rem  Huong dan chi tiet: docs\08-huong-dan-test-api.md
rem =====================================================================

cd /d "%~dp0.."
set PYTHONPATH=%CD%\services

start "iBanking-auth-service :8001"    cmd /k python -m uvicorn main:app --port 8001 --app-dir services\auth-service --reload
start "iBanking-payer-service :8002"   cmd /k python -m uvicorn main:app --port 8002 --app-dir services\payer-service --reload
start "iBanking-tuition-service :8003" cmd /k python -m uvicorn main:app --port 8003 --app-dir services\tuition-service --reload

echo.
echo  Da mo 3 cua so moi (auth :8001, payer :8002, tuition :8003)
echo  Test ngay:     python scripts\test_api.py
echo  Swagger UI:    http://localhost:8001/docs
echo.
pause