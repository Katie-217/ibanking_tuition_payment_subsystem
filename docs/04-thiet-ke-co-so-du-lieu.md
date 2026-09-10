# Tài liệu 04 — Thiết kế Cơ sở dữ liệu (SQL Server)

> Đáp ứng yêu cầu đề bài mục 1 (ERD) và mục 4 (thiết kế & hiện thực DB). Nguyên tắc: **Database per Service**, 6 database riêng trên cùng 1 SQL Server instance. ID tham chiếu giữa service chỉ là **reference id** — không tạo FK xuyên database.

## 1. Sơ đồ quan hệ tổng thể (ERD logic, theo ranh giới service)

```mermaid
erDiagram
    %% ===== AUTH =====
    USERS ||--|| USER_CREDENTIALS : "uid"

    %% ===== PAYER =====
    PAYERS ||--|| ACCOUNTS : "payer_uid"
    ACCOUNTS ||--o{ BALANCE_LEDGER : "account_id"

    %% ===== TUITION =====
    SCHOOLS ||--o{ FACULTIES : "school_id"
    FACULTIES ||--o{ MAJORS : "faculty_id"
    EDU_SYSTEMS ||--o{ STUDENTS : "system_id"
    SCHOOLS ||--o{ STUDENTS : "school_id"
    FACULTIES ||--o{ STUDENTS : "faculty_id"
    MAJORS ||--o{ STUDENTS : "major_id"
    STUDENTS ||--o{ TUITIONS : "student_id"
    TUITIONS ||--o{ ENROLLMENTS : "tuition_id (môn đã đăng ký)"
    SUBJECTS ||--o{ ENROLLMENTS : "subject_id"

    %% ===== PAYMENT =====
    PAYMENTS ||--o{ PAYMENT_HISTORY : "payment_id"

    %% ===== OTP =====
    OTPS }o--|| PAYMENTS : "payment_id (reference)"

    %% ===== NOTIFICATION =====
    EMAIL_OUTBOX }o--|| PAYMENTS : "payment_id (reference)"

    %% ===== Cross-service reference (KHÔNG FK) =====
    USERS ||--o| PAYERS : "uid (reference)"
    USERS ||--o{ PAYMENTS : "uid (reference)"
    STUDENTS ||--o{ PAYMENTS : "student_id (reference)"
    TUITIONS ||--o{ PAYMENTS : "tuition_id (reference)"

    USERS {
        int uid PK
        string username UK
        string full_name
        string phone
        string email
        string role
    }
    USER_CREDENTIALS {
        int credential_id PK
        int uid FK_UK
        string password_hash
    }
    PAYERS {
        int payer_uid PK
        string full_name
        string phone
        string email
    }
    ACCOUNTS {
        int account_id PK
        int payer_uid FK_UK
        decimal available_balance
    }
    BALANCE_LEDGER {
        bigint ledger_id PK
        int account_id FK
        bigint payment_id
        string change_type
        decimal amount
        decimal balance_after
    }
    SCHOOLS {
        string school_id PK
        string name
        string finance_email
        string beneficiary_name
        string bank_name
        string bank_account_no
    }
    FACULTIES {
        int faculty_id PK
        string school_id FK
        string faculty_code
        string name
    }
    MAJORS {
        int major_id PK
        int faculty_id FK
        string major_code
        string name
    }
    EDU_SYSTEMS {
        int system_id PK
        string system_code
        string name
    }
    STUDENTS {
        string student_id PK
        int uid
        string full_name
        string email
        string school_id FK
        int faculty_id FK
        int major_id FK
        int system_id FK
        string enrollment_year
    }
    TUITIONS {
        bigint tuition_id PK
        string student_id FK
        string semester
        decimal amount
        string status
        date due_date
        datetime2 paid_at
        bigint paid_by_payment_id
    }
    SUBJECTS {
        string subject_id PK
        string name
        tinyint credits
    }
    ENROLLMENTS {
        bigint enrollment_id PK
        bigint tuition_id FK
        string subject_id FK
        tinyint credits
        decimal amount
        datetime2 registered_at
    }
    PAYMENTS {
        bigint payment_id PK
        int uid
        string student_id
        bigint tuition_id
        decimal amount
        string status
        datetime2 expires_at
        string idempotency_key
    }
    PAYMENT_HISTORY {
        bigint history_id PK
        bigint payment_id FK
        string from_status
        string to_status
        string note
    }
    OTPS {
        bigint otp_id PK
        bigint payment_id UK
        string code UK
        tinyint attempts
        datetime2 expires_at
    }
    EMAIL_OUTBOX {
        bigint outbox_id PK
        bigint payment_id
        string to_email
        string recipient_type
        string template
        string status
        int attempts
    }
```

**Ghi chú:** đường nét đứt `(reference)` là liên kết logic qua API — không phải FK vật lý xuyên database.

## 2. DDL SQL Server

### 2.1 AuthDB

```sql
CREATE DATABASE AuthDB;
GO
USE AuthDB;
GO

CREATE TABLE users (
    uid         INT IDENTITY(1,1) PRIMARY KEY,
    username    NVARCHAR(20)  NOT NULL CONSTRAINT uq_users_username UNIQUE, -- MSSV TDTU, vd 521H0092
    full_name   NVARCHAR(100) NOT NULL,
    phone       NVARCHAR(15)  NULL,
    email       NVARCHAR(100) NOT NULL,
    role        NVARCHAR(20)  NOT NULL DEFAULT N'student',
    status      NVARCHAR(20)  NOT NULL DEFAULT N'ACTIVE', -- ACTIVE / LOCKED
    created_at  DATETIME2(0)  NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT chk_users_username CHECK (username LIKE '[0-9][0-9][0-9][A-Za-z][0-9][0-9][0-9][0-9]')
);

CREATE TABLE user_credentials (
    credential_id  INT IDENTITY(1,1) PRIMARY KEY,
    uid            INT NOT NULL CONSTRAINT uq_creds_uid UNIQUE
                   CONSTRAINT fk_creds_users FOREIGN KEY REFERENCES users(uid),
    password_hash  NVARCHAR(100) NOT NULL,   -- bcrypt
    updated_at     DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);
```

### 2.2 PayerDB

```sql
CREATE DATABASE PayerDB;
GO
USE PayerDB;
GO

CREATE TABLE payers (
    payer_uid  INT PRIMARY KEY,          -- reference auth.users.uid (không FK xuyên DB)
    full_name  NVARCHAR(100) NOT NULL,
    phone      NVARCHAR(15)  NULL,
    email      NVARCHAR(100) NOT NULL
);

CREATE TABLE accounts (
    account_id        BIGINT IDENTITY(1,1) PRIMARY KEY,
    payer_uid         INT NOT NULL CONSTRAINT uq_accounts_payer UNIQUE,
    available_balance DECIMAL(18,0) NOT NULL DEFAULT 0,
    currency          NCHAR(3) NOT NULL DEFAULT N'VND',
    rowversion        ROWVERSION,        -- optimistic lock
    CONSTRAINT chk_accounts_balance CHECK (available_balance >= 0),
    CONSTRAINT fk_accounts_payers FOREIGN KEY (payer_uid) REFERENCES payers(payer_uid)
);

CREATE TABLE balance_ledger (
    ledger_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
    account_id     BIGINT NOT NULL CONSTRAINT fk_ledger_accounts FOREIGN KEY REFERENCES accounts(account_id),
    payment_id     BIGINT NOT NULL,      -- reference payment-service.payments.payment_id
    change_type    NVARCHAR(20) NOT NULL CONSTRAINT chk_ledger_type CHECK (change_type IN (N'CAPTURE', N'RELEASE')),
    amount         DECIMAL(18,0) NOT NULL CHECK (amount > 0),
    balance_after  DECIMAL(18,0) NOT NULL,
    created_at     DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_ledger_idem UNIQUE (payment_id, change_type)  -- idempotency: 1 payment chỉ bị trừ 1 lần
);
CREATE INDEX ix_ledger_account ON balance_ledger(account_id, created_at DESC);
```

### 2.3 TuitionDB

> Bảng `students` là **bảng nhận diện sinh viên theo MSSV**: từ MSSV tra ngược về **trường → khoa → ngành** và **hệ/mã hệ**. Khi có quy tắc giải mã MSSV thật của TDTU, chỉ cần nạp lại dữ liệu `faculties`/`majors`/`edu_systems` và mapping trong `students`.

```sql
CREATE DATABASE TuitionDB;
GO
USE TuitionDB;
GO

-- Trường học (kèm thông tin NGƯỜI NHẬN học phí — hiển thị ở popup xác nhận thanh toán)
CREATE TABLE schools (
    school_id         NVARCHAR(20)  PRIMARY KEY,
    name              NVARCHAR(200) NOT NULL,
    finance_email     NVARCHAR(100) NOT NULL,  -- email bộ phận thu học phí
    beneficiary_name  NVARCHAR(200) NULL,      -- tên đơn vị thụ hưởng
    bank_name         NVARCHAR(200) NULL,      -- ngân hàng
    bank_account_no   NVARCHAR(30)  NULL       -- số tài khoản nhận học phí
);

-- Khoa (thuộc trường)
CREATE TABLE faculties (
    faculty_id   INT IDENTITY(1,1) PRIMARY KEY,
    school_id    NVARCHAR(20)  NOT NULL CONSTRAINT fk_faculties_schools FOREIGN KEY REFERENCES schools(school_id),
    faculty_code NVARCHAR(10)  NOT NULL,   -- mã khoa trong MSSV
    name         NVARCHAR(200) NOT NULL,
    CONSTRAINT uq_faculties_code UNIQUE (school_id, faculty_code)
);

-- Ngành (thuộc khoa)
CREATE TABLE majors (
    major_id   INT IDENTITY(1,1) PRIMARY KEY,
    faculty_id INT            NOT NULL CONSTRAINT fk_majors_faculties FOREIGN KEY REFERENCES faculties(faculty_id),
    major_code NVARCHAR(10)   NOT NULL,
    name       NVARCHAR(200)  NOT NULL,
    CONSTRAINT uq_majors_code UNIQUE (faculty_id, major_code)
);

-- Hệ đào tạo + mã hệ (kí tự trong MSSV)
CREATE TABLE edu_systems (
    system_id   INT IDENTITY(1,1) PRIMARY KEY,
    system_code NVARCHAR(10)  NOT NULL CONSTRAINT uq_edu_systems_code UNIQUE,  -- mã hệ
    name        NVARCHAR(100) NOT NULL                                         -- tên hệ
);

-- Bảng nhận diện sinh viên: MSSV -> trường/khoa/ngành/hệ
CREATE TABLE students (
    student_id      NVARCHAR(20) PRIMARY KEY,   -- MSSV, vd 521H0092
    uid             INT NOT NULL,               -- reference AuthDB.users.uid
    full_name       NVARCHAR(100) NOT NULL,
    phone           NVARCHAR(15)  NULL,
    email           NVARCHAR(100) NOT NULL,
    school_id       NVARCHAR(20) NOT NULL CONSTRAINT fk_students_schools   FOREIGN KEY REFERENCES schools(school_id),
    faculty_id      INT NOT NULL         CONSTRAINT fk_students_faculties FOREIGN KEY REFERENCES faculties(faculty_id),
    major_id        INT NOT NULL         CONSTRAINT fk_students_majors    FOREIGN KEY REFERENCES majors(major_id),
    system_id       INT NOT NULL         CONSTRAINT fk_students_systems   FOREIGN KEY REFERENCES edu_systems(system_id),
    enrollment_year NCHAR(2) NOT NULL,         -- khóa (2 số đầu MSSV)
    created_at      DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE UNIQUE INDEX ux_students_uid ON students(uid);

CREATE TABLE tuitions (
    tuition_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
    student_id          NVARCHAR(20) NOT NULL CONSTRAINT fk_tuitions_students FOREIGN KEY REFERENCES students(student_id),
    semester            NVARCHAR(30) NOT NULL,          -- vd N'2025-2026-HK1'
    amount              DECIMAL(18,0) NOT NULL CHECK (amount > 0),
    status              NVARCHAR(20) NOT NULL DEFAULT N'UNPAID'
                        CONSTRAINT chk_tuitions_status CHECK (status IN (N'UNPAID', N'PAYING', N'PAID')),
    due_date            DATE NOT NULL,
    paid_at             DATETIME2(0) NULL,
    paid_by_payment_id  BIGINT NULL,        -- reference payment
    rowversion          ROWVERSION,
    created_at          DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_tuitions_sem UNIQUE (student_id, semester)
);

-- Danh mục môn học (dữ liệu nền, dùng lại cho nhiều học kỳ)
CREATE TABLE subjects (
    subject_id  NVARCHAR(20)  PRIMARY KEY,      -- mã môn, vd N'IT101'
    name        NVARCHAR(200) NOT NULL,         -- tên môn
    credits     TINYINT       NOT NULL CHECK (credits > 0),
    created_at  DATETIME2(0)  NOT NULL DEFAULT SYSUTCDATETIME()
);

-- ĐĂNG KÝ MÔN HỌC: sinh viên đã đăng ký môn nào trong học kỳ đó + học phí của từng môn.
-- Đây là bảng để truy vấn danh sách môn hiển thị trên trang thanh toán.
-- tuition_id đã xác định duy nhất (student_id, semester) → không lặp lại 2 cột đó.
-- Bất biến dữ liệu: SUM(enrollments.amount) theo 1 tuition_id = tuitions.amount
CREATE TABLE enrollments (
    enrollment_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    tuition_id    BIGINT NOT NULL CONSTRAINT fk_enroll_tuitions  FOREIGN KEY REFERENCES tuitions(tuition_id),
    subject_id    NVARCHAR(20) NOT NULL CONSTRAINT fk_enroll_subjects FOREIGN KEY REFERENCES subjects(subject_id),
    credits       TINYINT NOT NULL CHECK (credits > 0),
    amount        DECIMAL(18,0) NOT NULL CHECK (amount > 0),   -- học phí môn này
    registered_at DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_enroll_tuition_subject UNIQUE (tuition_id, subject_id)  -- 1 môn không đăng ký 2 lần/học kỳ
);
CREATE INDEX ix_enroll_tuition ON enrollments(tuition_id);
```

**Truy vấn hiển thị bảng môn học của 1 học kỳ** (dùng bởi `GET /tuitions/{id}/enrollments`):

```sql
SELECT e.subject_id, s.name AS subject_name, e.credits, e.amount
FROM enrollments e
JOIN subjects s   ON s.subject_id = e.subject_id
JOIN tuitions t   ON t.tuition_id = e.tuition_id
JOIN students st  ON st.student_id = t.student_id
WHERE st.uid = @uid                      -- uid lấy từ JWT (BR-04)
  AND t.semester = N'2025-2026-HK1'      -- học kỳ sinh viên chọn
ORDER BY e.subject_id;

### 2.4 PaymentDB

```sql
CREATE DATABASE PaymentDB;
GO
USE PaymentDB;
GO

CREATE TABLE payments (
    payment_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
    uid              INT NOT NULL,               -- reference auth/users
    student_id       NVARCHAR(20) NOT NULL,      -- reference tuition/students (snapshot)
    tuition_id       BIGINT NOT NULL,            -- reference tuition/tuitions
    amount           DECIMAL(18,0) NOT NULL CHECK (amount > 0),
    status           NVARCHAR(20) NOT NULL DEFAULT N'PENDING'
                     CONSTRAINT chk_payments_status CHECK (status IN
                        (N'PENDING', N'OTP_SENT', N'PROCESSING', N'SUCCESS', N'FAILED', N'CANCELLED', N'EXPIRED')),
    failure_reason   NVARCHAR(200) NULL,
    idempotency_key  NVARCHAR(64) NULL,
    created_at       DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    expires_at       DATETIME2(0) NOT NULL,      -- created_at + 5 phút
    completed_at     DATETIME2(0) NULL
);
CREATE UNIQUE INDEX ux_payments_idem ON payments(idempotency_key) WHERE idempotency_key IS NOT NULL;

-- BR-07/BR-11 cấp DB:
-- (1) mỗi uid chỉ có tối đa 1 payment đang chờ xử lý
CREATE UNIQUE INDEX ux_payments_active
    ON payments(uid)
    WHERE status IN (N'PENDING', N'OTP_SENT', N'PROCESSING');
-- (2) mỗi tuition_id chỉ có đúng 1 payment SUCCESS  -> chặn double-pay case B ngay tại DB
CREATE UNIQUE INDEX ux_payments_success
    ON payments(tuition_id)
    WHERE status = N'SUCCESS';

CREATE TABLE payment_history (
    history_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
    payment_id   BIGINT NOT NULL CONSTRAINT fk_history_payments FOREIGN KEY REFERENCES payments(payment_id),
    from_status  NVARCHAR(20) NULL,
    to_status    NVARCHAR(20) NOT NULL,
    note         NVARCHAR(500) NULL,
    created_at   DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE INDEX ix_history_payment ON payment_history(payment_id, created_at);
```

### 2.5 OTPDB

> **Chính sách lưu trữ:** bảng `otps` giữ bản ghi trong suốt vòng đời OTP và dùng `status` để phân biệt
> `ACTIVE`, `EXPIRED`, `USED`, `INVALID`, `LOCKED`, `CANCELLED`, `REPLACED`. Chỉ tác vụ dọn dữ liệu
> riêng của OTPDB mới xóa bản ghi; không xóa ngay khi OTP hết hạn, đã dùng hoặc bị lỗi.

```sql
CREATE DATABASE OTPDB;
GO
USE OTPDB;
GO

CREATE TABLE otps (
    otp_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
    uid         INT NOT NULL,                         -- reference AuthDB, khóa theo tài khoản
    payment_id  BIGINT NOT NULL,                      -- reference PaymentDB
    code        CHAR(6) NOT NULL,
    status      NVARCHAR(20) NOT NULL DEFAULT N'ACTIVE',
    attempts    TINYINT NOT NULL DEFAULT 0,
    created_at  DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    expires_at  DATETIME2(0) NOT NULL,
    used_at     DATETIME2(0) NULL,
    invalidated_at DATETIME2(0) NULL,
    status_reason NVARCHAR(200) NULL,
    CONSTRAINT chk_otps_status CHECK (status IN
        (N'ACTIVE', N'EXPIRED', N'USED', N'INVALID', N'LOCKED', N'CANCELLED', N'REPLACED')),
    CONSTRAINT chk_otps_expiry CHECK (expires_at > created_at),
    CONSTRAINT chk_otps_code   CHECK (code LIKE '[0-9][0-9][0-9][0-9][0-9][0-9]')
);
CREATE UNIQUE INDEX ux_otps_active_uid ON otps(uid) WHERE status = N'ACTIVE';
CREATE UNIQUE INDEX ux_otps_active_payment ON otps(payment_id) WHERE status = N'ACTIVE';
CREATE UNIQUE INDEX ux_otps_active_code ON otps(code) WHERE status = N'ACTIVE';
CREATE INDEX ix_otps_expiry ON otps(status, expires_at);
```

> Lịch sử trạng thái OTP nằm ngay trong `otps`; tác vụ dọn dữ liệu có thể xóa các bản ghi không còn cần tra cứu.

### 2.6 NotificationDB

```sql
CREATE DATABASE NotificationDB;
GO
USE NotificationDB;
GO

CREATE TABLE email_outbox (
    outbox_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
    payment_id     BIGINT NULL,
    to_email       NVARCHAR(100) NOT NULL,
    recipient_type NVARCHAR(20) NOT NULL
                   CONSTRAINT chk_outbox_recipient CHECK (recipient_type IN (N'PAYER', N'SCHOOL')),
    template       NVARCHAR(30) NOT NULL
                   CONSTRAINT chk_outbox_template CHECK (template IN (N'OTP_EMAIL', N'CONFIRM_EMAIL')),
    subject        NVARCHAR(200) NOT NULL,
    body           NVARCHAR(MAX) NOT NULL,
    status         NVARCHAR(20) NOT NULL DEFAULT N'PENDING'
                   CONSTRAINT chk_outbox_status CHECK (status IN (N'PENDING', N'SENT', N'FAILED')),
    attempts       INT NOT NULL DEFAULT 0,
    last_error     NVARCHAR(500) NULL,
    created_at     DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    sent_at        DATETIME2(0) NULL
);
CREATE INDEX ix_outbox_pending ON email_outbox(status, attempts);
```

## 3. Seed data (dùng khi khởi tạo)

```sql
-- AuthDB
INSERT INTO users (username, full_name, phone, email) VALUES
(N'521H0092', N'Nguyễn Văn A', N'0901234567', N'521H0092@student.tdtu.edu.vn'),
(N'522H0145', N'Trần Thị B',     N'0909876543', N'522H0145@student.tdtu.edu.vn'),
(N'523H0201', N'Lê Minh C',      N'0912345678', N'523H0201@student.tdtu.edu.vn');

-- user_credentials: password_hash nc BCRYPT (script seed Python sẽ sinh nd) — ví dụ mật khẩu gốc "abc12345"
-- INSERT INTO user_credentials (uid, password_hash) VALUES (1, N'<bcrypt-hash>'), ...;

-- PayerDB
INSERT INTO payers (payer_uid, full_name, phone, email) VALUES
(1, N'Nguyễn Văn A', N'0901234567', N'521H0092@student.tdtu.edu.vn'),
(2, N'Trần Thị B',     N'0909876543', N'522H0145@student.tdtu.edu.vn'),
(3, N'Lê Minh C',      N'0912345678', N'523H0201@student.tdtu.edu.vn');

INSERT INTO accounts (payer_uid, available_balance) VALUES
(1, 15000000),   -- đủ trả
(2, 2000000),    -- đủ trả
(3, 1000000);    -- THIẾU dư để demo lỗi

-- TuitionDB
INSERT INTO schools (school_id, name, finance_email, beneficiary_name, bank_name, bank_account_no) VALUES
(N'TDTU', N'Trường Đại học Tôn Đức Thắng', N'hocphi@tdtu.edu.vn',
 N'TRUONG DAI HOC TON DUC THANG', N'Ngân hàng TMCP Công Thương Việt Nam (VietinBank)', N'117000123456');

INSERT INTO edu_systems (system_code, name) VALUES
(N'1', N'Đại học chính quy'),
(N'2', N'Đại học liên thông chính quy'),
(N'3', N'Cao đẳng chính quy');

INSERT INTO faculties (school_id, faculty_code, name) VALUES
(N'TDTU', N'00', N'Khoa Công nghệ thông tin'),
(N'TDTU', N'01', N'Khoa Quản trị kinh doanh');

INSERT INTO majors (faculty_id, major_code, name) VALUES
(1, N'CNTT', N'Công nghệ thông tin'),
(1, N'KTPM', N'Kỹ thuật phần mềm'),
(2, N'QTKD', N'Quản trị kinh doanh');

INSERT INTO students (student_id, uid, full_name, phone, email,
                      school_id, faculty_id, major_id, system_id, enrollment_year) VALUES
(N'521H0092', 1, N'Nguyễn Văn A', N'0901234567', N'521H0092@student.tdtu.edu.vn', N'TDTU', 1, 1, 1, N'52'),
(N'522H0145', 2, N'Trần Thị B',     N'0909876543', N'522H0145@student.tdtu.edu.vn', N'TDTU', 1, 2, 1, N'52'),
(N'523H0201', 3, N'Lê Minh C',      N'0912345678', N'523H0201@student.tdtu.edu.vn', N'TDTU', 2, 3, 1, N'52');
-- Mapping khoa/ngành/hệ là DEMO — cập nhật theo quy tắc giải mã MSSV thật khi có.

INSERT INTO tuitions (student_id, semester, amount, status, due_date) VALUES
(N'521H0092', N'2025-2026-HK1', 7000000, N'UNPAID', '2025-09-30'),
(N'522H0145', N'2025-2026-HK1', 1500000, N'UNPAID', '2025-09-30'),
(N'523H0201', N'2025-2026-HK1', 5000000, N'UNPAID', '2025-09-30'),  -- dư 1tr -> demo INSUFFICIENT
(N'523H0201', N'2024-2025-HK2', 5000000, N'PAID',   '2025-03-31');  -- demo TUITION_ALREADY_PAID

-- Môn học (500.000 đ / tín chỉ)
INSERT INTO subjects (subject_id, name, credits) VALUES
(N'IT101', N'Nhập môn lập trình', 3),
(N'IT102', N'Cấu trúc dữ liệu và giải thuật', 3),
(N'IT201', N'Cơ sở dữ liệu', 3),
(N'IT202', N'Kiến trúc hướng dịch vụ (SOA)', 3),
(N'MA101', N'Toán cao cấp', 2),
(N'EN101', N'Tiếng Anh 1', 2),
(N'EN102', N'Tiếng Anh 2', 2);

-- Môn đã đăng ký từng học kỳ (tuition_id 1..4 theo thứ tự INSERT tuitions ở trên)
-- HK1 của 521H0092: 14 tín chỉ = 7.000.000 (khớp tuitions.amount)
INSERT INTO enrollments (tuition_id, subject_id, credits, amount) VALUES
(1, N'IT101', 3, 1500000), (1, N'IT102', 3, 1500000), (1, N'IT201', 3, 1500000),
(1, N'IT202', 3, 1500000), (1, N'EN101', 2, 1000000),
(2, N'IT201', 3, 1500000),                                             -- 522H0145: 1.500.000
(3, N'IT101', 3, 1500000), (3, N'IT102', 3, 1500000),
(3, N'MA101', 2, 1000000), (3, N'EN101', 2, 1000000),                  -- 523H0201 HK1: 5.000.000
(4, N'IT201', 3, 1500000), (4, N'IT202', 3, 1500000),
(4, N'MA101', 2, 1000000), (4, N'EN102', 2, 1000000);                  -- 523H0201 HK2 (đã nộp)
```

## 4. Thiết kế DB phục vụ concurrency (quan trọng)

### 4.1 Case A — chống chi vượt số dư (nhiều GD cùng 1 tài khoản)

Capture tiền là **một câu UPDATE có điều kiện, nguyên tử** — không đọc rồi trừ 2 bước:

```sql
BEGIN TRANSACTION;
  UPDATE accounts
  SET available_balance = available_balance - @amount
  WHERE payer_uid = @uid AND available_balance >= @amount;   -- row lock tự động

  IF @@ROWCOUNT = 0
  BEGIN
    ROLLBACK;
    THROW 50422, N'INSUFFICIENT_BALANCE', 1;   -- 422 cho client
  END
  INSERT INTO balance_ledger (...) VALUES (...);
COMMIT;
```

- `CHECK (available_balance >= 0)` là lưới an toàn cuối cùng.
- `uq_ledger_idem UNIQUE (payment_id, change_type)` chống trừ 2 lần khi retry.
- Nếu muốn `SELECT ... WITH (UPDLOCK, ROWLOCK)` trước khi UPDATE để kiểm soát tường minh (pessimistic), giữ transaction ngắn.

### 4.2 Case B — chống double-pay cùng 1 khoản học phí

1. **Lock tuition** bằng conditional UPDATE:
   ```sql
   UPDATE tuitions SET status = N'PAYING'
   WHERE tuition_id = @id AND status = N'UNPAID';
   -- @@ROWCOUNT = 0 nghĩa là đã bị GD khác giữ hoặc đã PAID -> từ chối
   ```
2. **Tầng DB cuối cùng**: `ux_payments_success` (filtered unique index trên `tuition_id WHERE status='SUCCESS'`) — mọi nỗ lực insert 2 payment SUCCESS cho cùng 1 tuition sẽ ném lỗi unique ngay tại SQL Server.

### 4.3 Định danh & idempotency xuyên service

| Cơ chế | Nơi đặt | Chống gì |
|---|---|---|
| `uq_ledger_idem (payment_id, change_type)` | PayerDB | Trừ/hoàn tiền 2 lần |
| `uq_payments_active` | PaymentDB | 2 payment chờ cùng (uid, tuition) |
| `ux_payments_success` | PaymentDB | 2 payment SUCCESS cùng tuition |
| `uq_otps_payment (payment_id)` | OTPDB | 1 GD chỉ 1 OTP hiệu lực |
| `uq_otps_code (code)` | OTPDB | 2 OTP hiệu lực không trùng mã |
| `uq_creds_uid`, `uq_accounts_payer` | Auth/Payer | 1 user – 1 credential/account |

## 5. Quy tắc chung khi viết code data access

1. Mỗi service mở connection riêng tới database của mình (connection string per service trong env).
2. Tai liệu tham chiếu chéo: luôn đọc tươi qua API nội bộ (không cache dài hạn) cho balance & tuition status ngay trước khi quyết định.
3. Capture tiền và chuyển trạng thái tuition phải nằm trong transaction ngắn, không gọi mạng bên trong transaction.
4. `rowversion` để hỗ trợ optimistic check khi cần (đồ án ưu tiên pessimistic row lock vì dễ chứng minh).
5. Thời gian lưu **UTC** (`SYSUTCDATETIME()`), hiển thị chuyển về giờ VN ở frontend.
6. **OTP giữ lại trong DB cùng status** — verify thành công là `USED`, job quét là `EXPIRED`, hủy giao dịch là `CANCELLED`, resend là `REPLACED`. Tác vụ dọn dữ liệu riêng mới xóa bản ghi.