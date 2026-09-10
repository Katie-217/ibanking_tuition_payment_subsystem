-- =====================================================================
--  iBanking Tuition Payment — BƯỚC 1: TẠO 6 DATABASE (Database per Service)
--  Chạy trên SQL Server (SSMS). Có thể chạy lại nhiều lần (idempotent).
-- =====================================================================

IF DB_ID(N'AuthDB')         IS NULL CREATE DATABASE AuthDB;
IF DB_ID(N'PayerDB')        IS NULL CREATE DATABASE PayerDB;
IF DB_ID(N'TuitionDB')      IS NULL CREATE DATABASE TuitionDB;
IF DB_ID(N'PaymentDB')      IS NULL CREATE DATABASE PaymentDB;
IF DB_ID(N'OTPDB')          IS NULL CREATE DATABASE OTPDB;
IF DB_ID(N'NotificationDB') IS NULL CREATE DATABASE NotificationDB;
GO

-- Kiểm tra nhanh: phải thấy đủ 6 database
SELECT name AS database_name
FROM sys.databases
WHERE name IN (N'AuthDB', N'PayerDB', N'TuitionDB', N'PaymentDB', N'OTPDB', N'NotificationDB');
GO