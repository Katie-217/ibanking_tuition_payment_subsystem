-- =====================================================================
--  iBanking Tuition Payment — BƯỚC 2: TẠO SCHEMA CHO 6 DATABASE
--  Chạy sau khi tạo xong database. Có thể chạy lại (idempotent:
--  bảng/Khoá đã tồn tại thì bỏ qua).
--  Chi tiết thiết kế: docs/04-thiet-ke-co-so-du-lieu.md
-- =====================================================================

-- ============================= A. AuthDB =============================
USE AuthDB;
GO
IF OBJECT_ID(N'dbo.users', N'U') IS NULL
CREATE TABLE dbo.users (
    uid         INT IDENTITY(1,1) PRIMARY KEY,
    username    NVARCHAR(20)  NOT NULL CONSTRAINT uq_users_username UNIQUE,
    full_name   NVARCHAR(100) NOT NULL,
    phone       NVARCHAR(15)  NULL,
    email       NVARCHAR(100) NOT NULL,
    role        NVARCHAR(20)  NOT NULL CONSTRAINT df_users_role DEFAULT N'student',
    status      NVARCHAR(20)  NOT NULL CONSTRAINT df_users_status DEFAULT N'ACTIVE',
    created_at  DATETIME2(0)  NOT NULL CONSTRAINT df_users_created DEFAULT SYSUTCDATETIME(),
    -- MSSV TDTU: 3 số + 1 chữ + 4 số, vd 521H0092
    CONSTRAINT chk_users_username CHECK (username LIKE '[0-9][0-9][0-9][A-Za-z][0-9][0-9][0-9][0-9]'),
    CONSTRAINT chk_users_role   CHECK (role   IN (N'student', N'admin')),
    CONSTRAINT chk_users_status CHECK (status IN (N'ACTIVE', N'LOCKED'))
);
GO

IF OBJECT_ID(N'dbo.user_credentials', N'U') IS NULL
CREATE TABLE dbo.user_credentials (
    credential_id  INT IDENTITY(1,1) PRIMARY KEY,
    uid            INT NOT NULL CONSTRAINT uq_creds_uid UNIQUE
                   CONSTRAINT fk_creds_users FOREIGN KEY REFERENCES dbo.users(uid),
    password_hash  NVARCHAR(100) NOT NULL,   -- bcrypt
    updated_at     DATETIME2(0)  NOT NULL CONSTRAINT df_creds_updated DEFAULT SYSUTCDATETIME()
);
GO

-- ============================= B. PayerDB ============================
USE PayerDB;
GO
IF OBJECT_ID(N'dbo.payers', N'U') IS NULL
CREATE TABLE dbo.payers (
    payer_uid  INT PRIMARY KEY,              -- reference AuthDB.dbo.users.uid (không FK xuyên DB)
    full_name  NVARCHAR(100) NOT NULL,
    phone      NVARCHAR(15)  NULL,
    email      NVARCHAR(100) NOT NULL
);
GO

IF OBJECT_ID(N'dbo.accounts', N'U') IS NULL
CREATE TABLE dbo.accounts (
    account_id        BIGINT IDENTITY(1,1) PRIMARY KEY,
    payer_uid         INT NOT NULL CONSTRAINT uq_accounts_payer UNIQUE,
    available_balance DECIMAL(18,0) NOT NULL CONSTRAINT df_accounts_balance DEFAULT 0,
    currency          NCHAR(3) NOT NULL CONSTRAINT df_accounts_currency DEFAULT N'VND',
    rowversion        ROWVERSION,           -- optimistic lock
    CONSTRAINT chk_accounts_balance CHECK (available_balance >= 0),
    CONSTRAINT fk_accounts_payers FOREIGN KEY (payer_uid) REFERENCES dbo.payers(payer_uid)
);
GO

IF OBJECT_ID(N'dbo.balance_ledger', N'U') IS NULL
CREATE TABLE dbo.balance_ledger (
    ledger_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
    account_id     BIGINT NOT NULL CONSTRAINT fk_ledger_accounts FOREIGN KEY REFERENCES dbo.accounts(account_id),
    payment_id     BIGINT NOT NULL,         -- reference PaymentDB.dbo.payments.payment_id
    change_type    NVARCHAR(20) NOT NULL CONSTRAINT chk_ledger_type CHECK (change_type IN (N'CAPTURE', N'RELEASE')),
    amount         DECIMAL(18,0) NOT NULL CONSTRAINT chk_ledger_amount CHECK (amount > 0),
    balance_after  DECIMAL(18,0) NOT NULL,
    created_at     DATETIME2(0)  NOT NULL CONSTRAINT df_ledger_created DEFAULT SYSUTCDATETIME(),
    -- idempotency: 1 payment chỉ bị CAPTURE (hoặc RELEASE) đúng 1 lần
    CONSTRAINT uq_ledger_idem UNIQUE (payment_id, change_type)
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_ledger_account' AND object_id = OBJECT_ID(N'dbo.balance_ledger'))
    CREATE INDEX ix_ledger_account ON dbo.balance_ledger(account_id, created_at DESC);
GO

-- ============================ C. TuitionDB ===========================
USE TuitionDB;
GO

-- Trường học (kèm THÔNG TIN NGƯỜI NHẬN để hiển thị ở popup xác nhận thanh toán)
IF OBJECT_ID(N'dbo.schools', N'U') IS NULL
CREATE TABLE dbo.schools (
    school_id         NVARCHAR(20) PRIMARY KEY,
    name              NVARCHAR(200) NOT NULL,
    finance_email     NVARCHAR(100) NOT NULL,  -- email bộ phận thu học phí (nhận mail xác nhận)
    beneficiary_name  NVARCHAR(200) NULL,      -- tên người/đơn vị nhận tiền
    bank_name         NVARCHAR(200) NULL,      -- ngân hàng thụ hưởng
    bank_account_no   NVARCHAR(30)  NULL       -- số tài khoản nhận học phí
);
GO
-- Nếu DB đã tạo từ trước: thêm 3 cột người nhận (chạy lại nhiều lần vẫn an toàn)
IF COL_LENGTH(N'dbo.schools', N'beneficiary_name') IS NULL
    ALTER TABLE dbo.schools ADD beneficiary_name NVARCHAR(200) NULL;
GO
IF COL_LENGTH(N'dbo.schools', N'bank_name') IS NULL
    ALTER TABLE dbo.schools ADD bank_name NVARCHAR(200) NULL;
GO
IF COL_LENGTH(N'dbo.schools', N'bank_account_no') IS NULL
    ALTER TABLE dbo.schools ADD bank_account_no NVARCHAR(30) NULL;
GO

-- Khoa (thuộc trường)
IF OBJECT_ID(N'dbo.faculties', N'U') IS NULL
CREATE TABLE dbo.faculties (
    faculty_id   INT IDENTITY(1,1) PRIMARY KEY,
    school_id    NVARCHAR(20)  NOT NULL CONSTRAINT fk_faculties_schools FOREIGN KEY REFERENCES dbo.schools(school_id),
    faculty_code NVARCHAR(10)  NOT NULL,   -- mã khoa (xuất hiện trong MSSV nếu theo quy tắc giải mã)
    name         NVARCHAR(200) NOT NULL,
    CONSTRAINT uq_faculties_code UNIQUE (school_id, faculty_code)
);
GO

-- Ngành (thuộc khoa)
IF OBJECT_ID(N'dbo.majors', N'U') IS NULL
CREATE TABLE dbo.majors (
    major_id   INT IDENTITY(1,1) PRIMARY KEY,
    faculty_id INT NOT NULL CONSTRAINT fk_majors_faculties FOREIGN KEY REFERENCES dbo.faculties(faculty_id),
    major_code NVARCHAR(10)  NOT NULL,
    name       NVARCHAR(200) NOT NULL,
    CONSTRAINT uq_majors_code UNIQUE (faculty_id, major_code)
);
GO

-- Hệ đào tạo + mã hệ (kí tự trong MSSV)
IF OBJECT_ID(N'dbo.edu_systems', N'U') IS NULL
CREATE TABLE dbo.edu_systems (
    system_id   INT IDENTITY(1,1) PRIMARY KEY,
    system_code NVARCHAR(10)  NOT NULL CONSTRAINT uq_edu_systems_code UNIQUE,  -- mã hệ
    name        NVARCHAR(100) NOT NULL                                         -- tên hệ (ĐH chính quy, liên thông...)
);
GO

-- Bảng nhận diện sinh viên theo MSSV: MSSV -> trường / khoa / ngành / hệ
IF OBJECT_ID(N'dbo.students', N'U') IS NULL
CREATE TABLE dbo.students (
    student_id      NVARCHAR(20) PRIMARY KEY,   -- MSSV, vd 521H0092
    uid             INT NOT NULL,               -- reference AuthDB.dbo.users.uid
    full_name       NVARCHAR(100) NOT NULL,
    phone           NVARCHAR(15)  NULL,
    email           NVARCHAR(100) NOT NULL,
    school_id       NVARCHAR(20) NOT NULL CONSTRAINT fk_students_schools   FOREIGN KEY REFERENCES dbo.schools(school_id),
    faculty_id      INT NOT NULL         CONSTRAINT fk_students_faculties FOREIGN KEY REFERENCES dbo.faculties(faculty_id),
    major_id        INT NOT NULL         CONSTRAINT fk_students_majors    FOREIGN KEY REFERENCES dbo.majors(major_id),
    system_id       INT NOT NULL         CONSTRAINT fk_students_systems   FOREIGN KEY REFERENCES dbo.edu_systems(system_id),
    enrollment_year NCHAR(2) NOT NULL,         -- khóa (2 số đầu MSSV)
    created_at      DATETIME2(0)  NOT NULL CONSTRAINT df_students_created DEFAULT SYSUTCDATETIME()
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ux_students_uid' AND object_id = OBJECT_ID(N'dbo.students'))
    CREATE UNIQUE INDEX ux_students_uid ON dbo.students(uid);
GO

IF OBJECT_ID(N'dbo.tuitions', N'U') IS NULL
CREATE TABLE dbo.tuitions (
    tuition_id          BIGINT IDENTITY(1,1) PRIMARY KEY,
    student_id          NVARCHAR(20) NOT NULL CONSTRAINT fk_tuitions_students FOREIGN KEY REFERENCES dbo.students(student_id),
    semester            NVARCHAR(30) NOT NULL,
    amount              DECIMAL(18,0) NOT NULL CONSTRAINT chk_tuitions_amount CHECK (amount > 0),
    status              NVARCHAR(20) NOT NULL CONSTRAINT df_tuitions_status DEFAULT N'UNPAID'
                        CONSTRAINT chk_tuitions_status CHECK (status IN (N'UNPAID', N'PAYING', N'PAID')),
    due_date            DATE NOT NULL,
    paid_at             DATETIME2(0)  NULL,
    paid_by_payment_id  BIGINT NULL,         -- reference PaymentDB
    rowversion          ROWVERSION,
    created_at          DATETIME2(0)  NOT NULL CONSTRAINT df_tuitions_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_tuitions_sem UNIQUE (student_id, semester)
);
GO

-- Danh mục môn học (dữ liệu nền, dùng lại cho nhiều học kỳ)
IF OBJECT_ID(N'dbo.subjects', N'U') IS NULL
CREATE TABLE dbo.subjects (
    subject_id   NVARCHAR(20) PRIMARY KEY,          -- mã môn, vd N'IT101'
    name         NVARCHAR(200) NOT NULL,            -- tên môn
    credits      TINYINT NOT NULL CONSTRAINT chk_subjects_credits CHECK (credits > 0),
    created_at   DATETIME2(0) NOT NULL CONSTRAINT df_subjects_created DEFAULT SYSUTCDATETIME()
);
GO

-- Nếu lần chạy trước đã tạo bảng tên cũ 'tuition_items' thì đổi tên sang 'enrollments'
IF OBJECT_ID(N'dbo.tuition_items', N'U') IS NOT NULL AND OBJECT_ID(N'dbo.enrollments', N'U') IS NULL
BEGIN
    EXEC sp_rename N'dbo.tuition_items', N'enrollments';
    EXEC sp_rename N'dbo.enrollments.item_id', N'enrollment_id', N'COLUMN';
END
GO

-- BẢNG ĐĂNG KÝ MÔN HỌC: sinh viên đã đăng ký môn nào trong học kỳ đó + học phí của môn đó.
-- tuition_id đã xác định duy nhất (student_id, semester) nên không lặp lại 2 cột này.
-- Bất biến: SUM(enrollments.amount) của 1 tuition = tuitions.amount
IF OBJECT_ID(N'dbo.enrollments', N'U') IS NULL
CREATE TABLE dbo.enrollments (
    enrollment_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    tuition_id    BIGINT NOT NULL CONSTRAINT fk_enroll_tuitions FOREIGN KEY REFERENCES dbo.tuitions(tuition_id),
    subject_id    NVARCHAR(20) NOT NULL CONSTRAINT fk_enroll_subjects FOREIGN KEY REFERENCES dbo.subjects(subject_id),
    credits       TINYINT NOT NULL CONSTRAINT chk_enroll_credits CHECK (credits > 0),
    amount        DECIMAL(18,0) NOT NULL CONSTRAINT chk_enroll_amount CHECK (amount > 0),  -- học phí môn này
    registered_at DATETIME2(0) NOT NULL CONSTRAINT df_enroll_registered DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_enroll_tuition_subject UNIQUE (tuition_id, subject_id)  -- 1 môn không đăng ký 2 lần/học kỳ
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_enroll_tuition' AND object_id = OBJECT_ID(N'dbo.enrollments'))
    CREATE INDEX ix_enroll_tuition ON dbo.enrollments(tuition_id);
GO

-- ============================ D. PaymentDB ===========================
USE PaymentDB;
GO
IF OBJECT_ID(N'dbo.payments', N'U') IS NULL
CREATE TABLE dbo.payments (
    payment_id       BIGINT IDENTITY(1,1) PRIMARY KEY,
    uid              INT NOT NULL,               -- reference AuthDB
    student_id       NVARCHAR(20) NOT NULL,      -- reference TuitionDB (snapshot)
    tuition_id       BIGINT NOT NULL,            -- reference TuitionDB
    amount           DECIMAL(18,0) NOT NULL CONSTRAINT chk_payments_amount CHECK (amount > 0),
    status           NVARCHAR(20) NOT NULL CONSTRAINT df_payments_status DEFAULT N'PENDING'
                     CONSTRAINT chk_payments_status CHECK (status IN
                        (N'PENDING', N'OTP_SENT', N'PROCESSING', N'SUCCESS', N'FAILED', N'CANCELLED', N'EXPIRED')),
    failure_reason   NVARCHAR(200) NULL,
    idempotency_key  NVARCHAR(64)  NULL,
    created_at       DATETIME2(0)  NOT NULL CONSTRAINT df_payments_created DEFAULT SYSUTCDATETIME(),
    expires_at       DATETIME2(0)  NOT NULL,     -- created_at + 5 phút
    completed_at     DATETIME2(0)  NULL,
    active_uid      AS (CASE WHEN status IN (N'PENDING', N'OTP_SENT', N'PROCESSING') THEN uid END) PERSISTED
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ux_payments_idem' AND object_id = OBJECT_ID(N'dbo.payments'))
    CREATE UNIQUE INDEX ux_payments_idem ON dbo.payments(idempotency_key) WHERE idempotency_key IS NOT NULL;
GO
-- BR-07: mỗi tài khoản sinh viên chỉ có tối đa 1 giao dịch đang chờ xử lý.
-- Ràng buộc theo uid (không theo tuition_id) để không thể mở song song nhiều
-- khoản học phí và tạo nhiều OTP cho cùng một tài khoản.
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ux_payments_active' AND object_id = OBJECT_ID(N'dbo.payments'))
    DROP INDEX ux_payments_active ON dbo.payments;
IF COL_LENGTH(N'dbo.payments', N'active_uid') IS NULL
    ALTER TABLE dbo.payments ADD active_uid AS
        (CASE WHEN status IN (N'PENDING', N'OTP_SENT', N'PROCESSING') THEN uid END) PERSISTED;
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ux_payments_active' AND object_id = OBJECT_ID(N'dbo.payments'))
    CREATE UNIQUE INDEX ux_payments_active
        ON dbo.payments(active_uid)
        WHERE active_uid IS NOT NULL;
GO
-- BR-11: mỗi tuition chỉ có đúng 1 giao dịch SUCCESS (chặn double-pay ngay tại DB)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ux_payments_success' AND object_id = OBJECT_ID(N'dbo.payments'))
    CREATE UNIQUE INDEX ux_payments_success
        ON dbo.payments(tuition_id)
        WHERE status = N'SUCCESS';
GO

IF OBJECT_ID(N'dbo.payment_history', N'U') IS NULL
CREATE TABLE dbo.payment_history (
    history_id   BIGINT IDENTITY(1,1) PRIMARY KEY,
    payment_id   BIGINT NOT NULL CONSTRAINT fk_history_payments FOREIGN KEY REFERENCES dbo.payments(payment_id),
    from_status  NVARCHAR(20) NULL,
    to_status    NVARCHAR(20) NOT NULL,
    note         NVARCHAR(500) NULL,
    created_at   DATETIME2(0)  NOT NULL CONSTRAINT df_history_created DEFAULT SYSUTCDATETIME()
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_history_payment' AND object_id = OBJECT_ID(N'dbo.payment_history'))
    CREATE INDEX ix_history_payment ON dbo.payment_history(payment_id, created_at);
GO

-- ============================== E. OTPDB =============================
USE OTPDB;
GO

-- CHÍNH SÁCH LƯU TRỮ OTP:
--   Bản ghi vẫn được giữ để biết vòng đời OTP; status mô tả kết quả cuối cùng.
--   Chỉ xóa bản ghi khi có tác vụ dọn dữ liệu riêng trong OTPDB.
IF OBJECT_ID(N'dbo.otps', N'U') IS NULL
CREATE TABLE dbo.otps (
    otp_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
    uid         INT NOT NULL,                                        -- reference AuthDB, dùng để khóa theo tài khoản
    payment_id  BIGINT NOT NULL,                                     -- reference PaymentDB
    code        CHAR(6) NOT NULL,
    status      NVARCHAR(20) NOT NULL CONSTRAINT df_otps_status DEFAULT N'ACTIVE',
    attempts    TINYINT NOT NULL CONSTRAINT df_otps_attempts DEFAULT 0,
    created_at  DATETIME2(0) NOT NULL CONSTRAINT df_otps_created DEFAULT SYSUTCDATETIME(),
    expires_at  DATETIME2(0) NOT NULL,
    used_at     DATETIME2(0) NULL,
    invalidated_at DATETIME2(0) NULL,
    status_reason NVARCHAR(200) NULL,
    CONSTRAINT chk_otps_status CHECK (status IN
        (N'ACTIVE', N'EXPIRED', N'USED', N'INVALID', N'LOCKED', N'CANCELLED', N'REPLACED')),
    CONSTRAINT chk_otps_expiry CHECK (expires_at > created_at),
    CONSTRAINT chk_otps_code   CHECK (code LIKE '[0-9][0-9][0-9][0-9][0-9][0-9]')
);
GO
-- Migration cho OTPDB đã tồn tại từ schema cũ.
IF OBJECT_ID(N'dbo.otps', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH(N'dbo.otps', N'uid') IS NULL
        ALTER TABLE dbo.otps ADD uid INT NULL;
    IF COL_LENGTH(N'dbo.otps', N'status') IS NULL
        ALTER TABLE dbo.otps ADD status NVARCHAR(20) NOT NULL
            CONSTRAINT df_otps_status_migrated DEFAULT N'ACTIVE';
    IF COL_LENGTH(N'dbo.otps', N'used_at') IS NULL
        ALTER TABLE dbo.otps ADD used_at DATETIME2(0) NULL;
    IF COL_LENGTH(N'dbo.otps', N'invalidated_at') IS NULL
        ALTER TABLE dbo.otps ADD invalidated_at DATETIME2(0) NULL;
    IF COL_LENGTH(N'dbo.otps', N'status_reason') IS NULL
        ALTER TABLE dbo.otps ADD status_reason NVARCHAR(200) NULL;

    UPDATE o
    SET uid = p.uid
    FROM dbo.otps o
    JOIN PaymentDB.dbo.payments p ON p.payment_id = o.payment_id
    WHERE o.uid IS NULL;

    IF EXISTS (SELECT 1 FROM dbo.otps WHERE uid IS NULL)
        THROW 51001, 'Khong the migrate OTP vi thieu uid cua payment', 1;

    ALTER TABLE dbo.otps ALTER COLUMN uid INT NOT NULL;
    IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'uq_otps_payment' AND parent_object_id = OBJECT_ID(N'dbo.otps'))
        ALTER TABLE dbo.otps DROP CONSTRAINT uq_otps_payment;
    IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'uq_otps_code' AND parent_object_id = OBJECT_ID(N'dbo.otps'))
        ALTER TABLE dbo.otps DROP CONSTRAINT uq_otps_code;
    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'chk_otps_status' AND parent_object_id = OBJECT_ID(N'dbo.otps'))
        ALTER TABLE dbo.otps ADD CONSTRAINT chk_otps_status CHECK (status IN
            (N'ACTIVE', N'EXPIRED', N'USED', N'INVALID', N'LOCKED', N'CANCELLED', N'REPLACED'));
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ux_otps_active_uid' AND object_id = OBJECT_ID(N'dbo.otps'))
    CREATE UNIQUE INDEX ux_otps_active_uid ON dbo.otps(uid)
        WHERE status = N'ACTIVE';                                  -- 1 OTP hiệu lực / tài khoản
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ux_otps_active_payment' AND object_id = OBJECT_ID(N'dbo.otps'))
    CREATE UNIQUE INDEX ux_otps_active_payment ON dbo.otps(payment_id)
        WHERE status = N'ACTIVE';                                  -- 1 OTP hiệu lực / giao dịch
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ux_otps_active_code' AND object_id = OBJECT_ID(N'dbo.otps'))
    CREATE UNIQUE INDEX ux_otps_active_code ON dbo.otps(code)
        WHERE status = N'ACTIVE';                                  -- không trùng mã đang hiệu lực
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_otps_expiry' AND object_id = OBJECT_ID(N'dbo.otps'))
    CREATE INDEX ix_otps_expiry ON dbo.otps(status, expires_at);
GO

-- ========================== F. NotificationDB =======================
USE NotificationDB;
GO
IF OBJECT_ID(N'dbo.email_outbox', N'U') IS NULL
CREATE TABLE dbo.email_outbox (
    outbox_id      BIGINT IDENTITY(1,1) PRIMARY KEY,
    payment_id     BIGINT NULL,                -- reference PaymentDB
    to_email       NVARCHAR(100) NOT NULL,
    recipient_type NVARCHAR(20)  NOT NULL
                   CONSTRAINT chk_outbox_recipient CHECK (recipient_type IN (N'PAYER', N'SCHOOL')),
    template       NVARCHAR(30)  NOT NULL
                   CONSTRAINT chk_outbox_template CHECK (template IN (N'OTP_EMAIL', N'CONFIRM_EMAIL')),
    subject        NVARCHAR(200) NOT NULL,
    body           NVARCHAR(MAX) NOT NULL,
    status         NVARCHAR(20)  NOT NULL CONSTRAINT df_outbox_status DEFAULT N'PENDING'
                   CONSTRAINT chk_outbox_status CHECK (status IN (N'PENDING', N'SENT', N'FAILED')),
    attempts       INT NOT NULL CONSTRAINT df_outbox_attempts DEFAULT 0,
    last_error     NVARCHAR(500) NULL,
    created_at     DATETIME2(0)  NOT NULL CONSTRAINT df_outbox_created DEFAULT SYSUTCDATETIME(),
    sent_at        DATETIME2(0)  NULL
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_outbox_pending' AND object_id = OBJECT_ID(N'dbo.email_outbox'))
    CREATE INDEX ix_outbox_pending ON dbo.email_outbox(status, attempts);
GO

PRINT N'>>> Tạo schema xong cho 6 database: AuthDB, PayerDB, TuitionDB, PaymentDB, OTPDB, NotificationDB';
GO