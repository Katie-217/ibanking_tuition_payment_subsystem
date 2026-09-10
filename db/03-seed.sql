-- =====================================================================
--  iBanking Tuition Payment — BƯỚC 3: SEED DỮ LIỆU DEMO
--  Chạy sau bước 1 + 2. Có thể chạy lại (bỏ qua bản ghi đã có).
--
--  3 tài khoản demo (mật khẩu mặc định gợi ý: abc12345):
--    + 521H0092  Nguyễn Văn A  - Số dư 15.000.000, học phí 7.000.000  -> ĐỦ TRẢ
--    + 522H0145  Trần Thị B    - Số dư  2.000.000, học phí 1.500.000  -> ĐỦ TRẢ
--    + 523H0201  Lê Minh C     - Số dư  1.000.000, học phí 5.000.000  -> THIẾU DƯ (demo lỗi)
--                               + 1 khoản PAID (2024-2025-HK2)        -> demo TUITION_ALREADY_PAID
--
--  MẬT KHẨU: bảng user_credentials cần hash bcrypt -> chạy
--  "python generate_password_hashes.py" rồi dán các dòng UPDATE in ra.
-- =====================================================================

-- ============================= A. AuthDB =============================
USE AuthDB;
GO
IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE username = N'521H0092')
    INSERT INTO dbo.users (username, full_name, phone, email) VALUES
    (N'521H0092', N'Nguyễn Văn A', N'0901234567', N'521H0092@student.tdtu.edu.vn');
IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE username = N'522H0145')
    INSERT INTO dbo.users (username, full_name, phone, email) VALUES
    (N'522H0145', N'Trần Thị B', N'0909876543', N'522H0145@student.tdtu.edu.vn');
IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE username = N'523H0201')
    INSERT INTO dbo.users (username, full_name, phone, email) VALUES
    (N'523H0201', N'Lê Minh C', N'0912345678', N'523H0201@student.tdtu.edu.vn');
GO

-- Placeholder hash -> thay bằng UPDATE từ generate_password_hashes.py
INSERT INTO dbo.user_credentials (uid, password_hash)
SELECT u.uid, N'TO_BE_SET'
FROM dbo.users u
WHERE NOT EXISTS (SELECT 1 FROM dbo.user_credentials c WHERE c.uid = u.uid);
GO

-- ============================= B. PayerDB ============================
USE PayerDB;
GO
INSERT INTO dbo.payers (payer_uid, full_name, phone, email)
SELECT u.uid, u.full_name, u.phone, u.email
FROM AuthDB.dbo.users u
WHERE u.username IN (N'521H0092', N'522H0145', N'523H0201')
  AND NOT EXISTS (SELECT 1 FROM dbo.payers p WHERE p.payer_uid = u.uid);
GO

INSERT INTO dbo.accounts (payer_uid, available_balance)
SELECT u.uid,
       CASE u.username
           WHEN N'521H0092' THEN 15000000
           WHEN N'522H0145' THEN 2000000
           WHEN N'523H0201' THEN 1000000
       END
FROM AuthDB.dbo.users u
WHERE u.username IN (N'521H0092', N'522H0145', N'523H0201')
  AND NOT EXISTS (SELECT 1 FROM dbo.accounts a WHERE a.payer_uid = u.uid);
GO

-- ============================ C. TuitionDB ===========================
USE TuitionDB;
GO
IF NOT EXISTS (SELECT 1 FROM dbo.schools WHERE school_id = N'TDTU')
    INSERT INTO dbo.schools (school_id, name, finance_email, beneficiary_name, bank_name, bank_account_no) VALUES
    (N'TDTU', N'Trường Đại học Tôn Đức Thắng', N'hocphi@tdtu.edu.vn',
     N'TRUONG DAI HOC TON DUC THANG', N'Ngân hàng TMCP Công Thương Việt Nam (VietinBank)', N'117000123456');
GO
-- Nếu trường đã có sẵn từ lần chạy trước: bổ sung thông tin người nhận
UPDATE dbo.schools
   SET beneficiary_name = N'TRUONG DAI HOC TON DUC THANG',
       bank_name        = N'Ngân hàng TMCP Công Thương Việt Nam (VietinBank)',
       bank_account_no  = N'117000123456'
 WHERE school_id = N'TDTU' AND beneficiary_name IS NULL;
GO

-- Hệ + mã hệ (demo — cập nhật theo quy tắc giải mã MSSV thật khi có)
IF NOT EXISTS (SELECT 1 FROM dbo.edu_systems WHERE system_code = N'1')
    INSERT INTO dbo.edu_systems (system_code, name) VALUES (N'1', N'Đại học chính quy');
IF NOT EXISTS (SELECT 1 FROM dbo.edu_systems WHERE system_code = N'2')
    INSERT INTO dbo.edu_systems (system_code, name) VALUES (N'2', N'Đại học liên thông chính quy');
IF NOT EXISTS (SELECT 1 FROM dbo.edu_systems WHERE system_code = N'3')
    INSERT INTO dbo.edu_systems (system_code, name) VALUES (N'3', N'Cao đẳng chính quy');
GO

-- Khoa (demo)
IF NOT EXISTS (SELECT 1 FROM dbo.faculties WHERE school_id = N'TDTU' AND faculty_code = N'00')
    INSERT INTO dbo.faculties (school_id, faculty_code, name) VALUES
    (N'TDTU', N'00', N'Khoa Công nghệ thông tin');
IF NOT EXISTS (SELECT 1 FROM dbo.faculties WHERE school_id = N'TDTU' AND faculty_code = N'01')
    INSERT INTO dbo.faculties (school_id, faculty_code, name) VALUES
    (N'TDTU', N'01', N'Khoa Quản trị kinh doanh');
GO

-- Ngành (demo — faculty_id lấy theo faculty_code ở trên)
IF NOT EXISTS (SELECT 1 FROM dbo.majors m JOIN dbo.faculties f ON m.faculty_id = f.faculty_id
               WHERE f.school_id = N'TDTU' AND f.faculty_code = N'00' AND m.major_code = N'CNTT')
    INSERT INTO dbo.majors (faculty_id, major_code, name)
    SELECT f.faculty_id, N'CNTT', N'Công nghệ thông tin' FROM dbo.faculties f
    WHERE f.school_id = N'TDTU' AND f.faculty_code = N'00';
IF NOT EXISTS (SELECT 1 FROM dbo.majors m JOIN dbo.faculties f ON m.faculty_id = f.faculty_id
               WHERE f.school_id = N'TDTU' AND f.faculty_code = N'00' AND m.major_code = N'KTPM')
    INSERT INTO dbo.majors (faculty_id, major_code, name)
    SELECT f.faculty_id, N'KTPM', N'Kỹ thuật phần mềm' FROM dbo.faculties f
    WHERE f.school_id = N'TDTU' AND f.faculty_code = N'00';
IF NOT EXISTS (SELECT 1 FROM dbo.majors m JOIN dbo.faculties f ON m.faculty_id = f.faculty_id
               WHERE f.school_id = N'TDTU' AND f.faculty_code = N'01' AND m.major_code = N'QTKD')
    INSERT INTO dbo.majors (faculty_id, major_code, name)
    SELECT f.faculty_id, N'QTKD', N'Quản trị kinh doanh' FROM dbo.faculties f
    WHERE f.school_id = N'TDTU' AND f.faculty_code = N'01';
GO

-- Bảng nhận diện sinh viên (MSSV -> trường/khoa/ngành/hệ)
-- Lưu ý: mapping khoa/ngành/hệ là DEMO — chỉnh lại theo quy tắc giải mã MSSV thật khi có.
IF NOT EXISTS (SELECT 1 FROM dbo.students WHERE student_id = N'521H0092')
        INSERT INTO dbo.students (student_id, uid, full_name, phone, email, school_id, faculty_id, major_id, system_id, enrollment_year)
        SELECT N'521H0092', u.uid, u.full_name, u.phone, u.email,
           s.school_id, f.faculty_id, m.major_id, e.system_id, N'52'
        FROM dbo.schools s, dbo.faculties f, dbo.majors m, dbo.edu_systems e
        JOIN AuthDB.dbo.users u ON u.username = N'521H0092'
    WHERE s.school_id = N'TDTU' AND f.school_id = N'TDTU' AND f.faculty_code = N'00'
      AND m.faculty_id = f.faculty_id AND m.major_code = N'CNTT' AND e.system_code = N'1';
IF NOT EXISTS (SELECT 1 FROM dbo.students WHERE student_id = N'522H0145')
        INSERT INTO dbo.students (student_id, uid, full_name, phone, email, school_id, faculty_id, major_id, system_id, enrollment_year)
        SELECT N'522H0145', u.uid, u.full_name, u.phone, u.email,
           s.school_id, f.faculty_id, m.major_id, e.system_id, N'52'
        FROM dbo.schools s, dbo.faculties f, dbo.majors m, dbo.edu_systems e
        JOIN AuthDB.dbo.users u ON u.username = N'522H0145'
    WHERE s.school_id = N'TDTU' AND f.school_id = N'TDTU' AND f.faculty_code = N'00'
      AND m.faculty_id = f.faculty_id AND m.major_code = N'KTPM' AND e.system_code = N'1';
IF NOT EXISTS (SELECT 1 FROM dbo.students WHERE student_id = N'523H0201')
        INSERT INTO dbo.students (student_id, uid, full_name, phone, email, school_id, faculty_id, major_id, system_id, enrollment_year)
        SELECT N'523H0201', u.uid, u.full_name, u.phone, u.email,
           s.school_id, f.faculty_id, m.major_id, e.system_id, N'52'
        FROM dbo.schools s, dbo.faculties f, dbo.majors m, dbo.edu_systems e
        JOIN AuthDB.dbo.users u ON u.username = N'523H0201'
    WHERE s.school_id = N'TDTU' AND f.school_id = N'TDTU' AND f.faculty_code = N'01'
      AND m.faculty_id = f.faculty_id AND m.major_code = N'QTKD' AND e.system_code = N'1';
GO

IF NOT EXISTS (SELECT 1 FROM dbo.tuitions WHERE student_id = N'521H0092' AND semester = N'2025-2026-HK1')
    INSERT INTO dbo.tuitions (student_id, semester, amount, status, due_date) VALUES
    (N'521H0092', N'2025-2026-HK1', 7000000, N'UNPAID', '2026-12-31');
IF NOT EXISTS (SELECT 1 FROM dbo.tuitions WHERE student_id = N'522H0145' AND semester = N'2025-2026-HK1')
    INSERT INTO dbo.tuitions (student_id, semester, amount, status, due_date) VALUES
    (N'522H0145', N'2025-2026-HK1', 1500000, N'UNPAID', '2026-12-31');
IF NOT EXISTS (SELECT 1 FROM dbo.tuitions WHERE student_id = N'523H0201' AND semester = N'2025-2026-HK1')
    INSERT INTO dbo.tuitions (student_id, semester, amount, status, due_date) VALUES
    (N'523H0201', N'2025-2026-HK1', 5000000, N'UNPAID', '2026-12-31');
IF NOT EXISTS (SELECT 1 FROM dbo.tuitions WHERE student_id = N'523H0201' AND semester = N'2024-2025-HK2')
    INSERT INTO dbo.tuitions (student_id, semester, amount, status, due_date, paid_at) VALUES
    (N'523H0201', N'2024-2025-HK2', 5000000, N'PAID', '2025-03-31', SYSUTCDATETIME());
GO

-- ---------------- Danh mục môn học (500.000 đ / tín chỉ) ----------------
IF NOT EXISTS (SELECT 1 FROM dbo.subjects WHERE subject_id = N'IT101')
    INSERT INTO dbo.subjects (subject_id, name, credits) VALUES (N'IT101', N'Nhập môn lập trình', 3);
IF NOT EXISTS (SELECT 1 FROM dbo.subjects WHERE subject_id = N'IT102')
    INSERT INTO dbo.subjects (subject_id, name, credits) VALUES (N'IT102', N'Cấu trúc dữ liệu và giải thuật', 3);
IF NOT EXISTS (SELECT 1 FROM dbo.subjects WHERE subject_id = N'IT201')
    INSERT INTO dbo.subjects (subject_id, name, credits) VALUES (N'IT201', N'Cơ sở dữ liệu', 3);
IF NOT EXISTS (SELECT 1 FROM dbo.subjects WHERE subject_id = N'IT202')
    INSERT INTO dbo.subjects (subject_id, name, credits) VALUES (N'IT202', N'Kiến trúc hướng dịch vụ (SOA)', 3);
IF NOT EXISTS (SELECT 1 FROM dbo.subjects WHERE subject_id = N'MA101')
    INSERT INTO dbo.subjects (subject_id, name, credits) VALUES (N'MA101', N'Toán cao cấp', 2);
IF NOT EXISTS (SELECT 1 FROM dbo.subjects WHERE subject_id = N'EN101')
    INSERT INTO dbo.subjects (subject_id, name, credits) VALUES (N'EN101', N'Tiếng Anh 1', 2);
IF NOT EXISTS (SELECT 1 FROM dbo.subjects WHERE subject_id = N'EN102')
    INSERT INTO dbo.subjects (subject_id, name, credits) VALUES (N'EN102', N'Tiếng Anh 2', 2);
GO

-- ---- Đăng ký môn học từng học kỳ (SUM amount mỗi học kỳ = tuitions.amount) ----
;WITH src(student_id, semester, subject_id, credits, amount) AS (
    SELECT * FROM (VALUES
        -- 521H0092 · 2025-2026-HK1 · 14 tín chỉ = 7.000.000
        (N'521H0092', N'2025-2026-HK1', N'IT101', 3, 1500000),
        (N'521H0092', N'2025-2026-HK1', N'IT102', 3, 1500000),
        (N'521H0092', N'2025-2026-HK1', N'IT201', 3, 1500000),
        (N'521H0092', N'2025-2026-HK1', N'IT202', 3, 1500000),
        (N'521H0092', N'2025-2026-HK1', N'EN101', 2, 1000000),
        -- 522H0145 · 2025-2026-HK1 · 3 tín chỉ = 1.500.000
        (N'522H0145', N'2025-2026-HK1', N'IT201', 3, 1500000),
        -- 523H0201 · 2025-2026-HK1 · 10 tín chỉ = 5.000.000
        (N'523H0201', N'2025-2026-HK1', N'IT101', 3, 1500000),
        (N'523H0201', N'2025-2026-HK1', N'IT102', 3, 1500000),
        (N'523H0201', N'2025-2026-HK1', N'MA101', 2, 1000000),
        (N'523H0201', N'2025-2026-HK1', N'EN101', 2, 1000000),
        -- 523H0201 · 2024-2025-HK2 (đã nộp) · 10 tín chỉ = 5.000.000
        (N'523H0201', N'2024-2025-HK2', N'IT201', 3, 1500000),
        (N'523H0201', N'2024-2025-HK2', N'IT202', 3, 1500000),
        (N'523H0201', N'2024-2025-HK2', N'MA101', 2, 1000000),
        (N'523H0201', N'2024-2025-HK2', N'EN102', 2, 1000000)
    ) v(student_id, semester, subject_id, credits, amount)
)
INSERT INTO dbo.enrollments (tuition_id, subject_id, credits, amount)
SELECT t.tuition_id, s.subject_id, s.credits, s.amount
FROM src s
JOIN dbo.tuitions t ON t.student_id = s.student_id AND t.semester = s.semester
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.enrollments e
    WHERE e.tuition_id = t.tuition_id AND e.subject_id = s.subject_id
);
GO

-- Kiểm tra bất biến: tổng học phí các môn đã đăng ký = số tiền học kỳ (không ra dòng nào = đúng)
SELECT t.tuition_id, t.student_id, t.semester, t.amount AS tuition_amount, SUM(e.amount) AS enrolled_total
FROM dbo.tuitions t JOIN dbo.enrollments e ON e.tuition_id = t.tuition_id
GROUP BY t.tuition_id, t.student_id, t.semester, t.amount
HAVING SUM(e.amount) <> t.amount;
GO

PRINT N'>>> Seed xong. Nhớ: chạy generate_password_hashes.py và dán UPDATE để set mật khẩu (bước 4).';
GO