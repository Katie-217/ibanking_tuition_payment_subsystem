@echo off
rem =====================================================================
rem  iBanking Tuition Payment - KHOI DONG DU 7 SERVICE
rem
rem  Cong va service:
rem    :8000 api-gateway        (cong vao duy nhat cua frontend)
rem    :8001 auth-service       (dang nhap, JWT)
rem    :8002 payer-service      (ho so + so du, tru/hoan tien)
rem    :8003 tuition-service    (danh sach hoc phi, khoa/mo trang thai)
rem    :8004 payment-service    (orchestrator + job quet het han)
rem    :8005 otp-service        (sinh/xac thuc OTP)
rem    :8006 notification-service (email OTP + xac nhan, Gmail SMTP)
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
set PYTHONIOENCODING=utf-8

start "iBanking-auth-service :8001"         cmd /k python -m uvicorn main:app --port 8001 --app-dir services\auth-service --reload
start "iBanking-payer-service :8002"        cmd /k python -m uvicorn main:app --port 8002 --app-dir services\payer-service --reload
start "iBanking-tuition-service :8003"      cmd /k python -m uvicorn main:app --port 8003 --app-dir services\tuition-service --reload
start "iBanking-payment-service :8004"      cmd /k python -m uvicorn main:app --port 8004 --app-dir services\payment-service --reload
start "iBanking-otp-service :8005"          cmd /k python -m uvicorn main:app --port 8005 --app-dir services\otp-service --reload
start "iBanking-notification-service :8006" cmd /k python -m uvicorn main:app --port 8006 --app-dir services\notification-service --reload
timeout /t 3 /nobreak >nul
start "iBanking-api-gateway :8000"          cmd /k python -m uvicorn main:app --port 8000 --app-dir services\api-gateway --reload

echo.
echo  Da mo 7 cua so moi: gateway :8000 + 6 service (8001-8006)
echo  Trang thai tong hop: http://localhost:8000/health
echo  Test toan he thong:  python scripts\test_payment.py   (yeu cau du 7 service)
echo  Test tung phan:      python scripts\test_api.py  /  test_otp.py  /  test_notification.py
echo  Frontend mo file:    frontend\index.html
echo.
pause
