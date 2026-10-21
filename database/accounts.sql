USE qr_attendance;

INSERT INTO users (role, employee_no, first_name, last_name, email, password_hash, status) VALUES
  ('admin', 'ADMIN-001', 'System', 'Administrator', 'admin124@attendance.ph', '3048275999cded43c82b0f7a765428a4:76117b8e3414e3839f748fbd4d4f9f2e7eea809c285d8ece39084127c96876e4', 'ACTIVE'),
  ('teacher', 'TCH-001', 'Juan', 'Dela Cruz', 'teacher@attendance.ph', '8a7dc36130e783cf7749e7caf0cdea8d:d97b3c407c4bd21572cdbca48d1c8d6c6e117dc941d711377d95f2cd500d24cb', 'ACTIVE'),
  ('staff', 'STF-001', 'Maria', 'Santos', 'staff@attendance.ph', '0bf18c2d5de531d893482903fd978390:31aaeeee5320cf6ac561043195e4f4cf0a0de20af85643548f5969f18b03f919', 'ACTIVE')
ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash), status = 'ACTIVE';
