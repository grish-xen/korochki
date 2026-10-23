-- Выполните от имени администратора MySQL после замены примерных паролей.
CREATE DATABASE IF NOT EXISTS korochki CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'korochki_user'@'localhost' IDENTIFIED BY 'REPLACE_WITH_STRONG_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON korochki.* TO 'korochki_user'@'localhost';
CREATE USER IF NOT EXISTS 'korochki_admin'@'localhost' IDENTIFIED BY 'REPLACE_WITH_DIFFERENT_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON korochki.* TO 'korochki_admin'@'localhost';
