-- AutoAssemble Vehicle Assembly Cloud Portal Database Schema
-- Compatible with MySQL 8.0+ and MariaDB

CREATE DATABASE IF NOT EXISTS `auto_assemble_db`;
USE `auto_assemble_db`;

-- Drop tables in reverse order of dependencies if they exist
DROP TABLE IF EXISTS `activity_logs`;
DROP TABLE IF EXISTS `reports`;
DROP TABLE IF EXISTS `tasks`;
DROP TABLE IF EXISTS `employees`;
DROP TABLE IF EXISTS `production_orders`;
DROP TABLE IF EXISTS `vehicles`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `roles`;

-- 1. Roles Table
CREATE TABLE `roles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Users Table
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role_id` INT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`role_id`) REFERENCES `roles`(`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Vehicles Table
CREATE TABLE `vehicles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `model` VARCHAR(100) NOT NULL,
    `type` VARCHAR(50) NOT NULL, -- SUV, Sedan, Truck, Electric, etc.
    `assembly_line` VARCHAR(100) NOT NULL, -- Line A, Line B, etc.
    `status` VARCHAR(50) NOT NULL DEFAULT 'Planned', -- Planned, In Progress, Quality Check, Completed, Delayed
    `start_date` DATE DEFAULT NULL,
    `completion_date` DATE DEFAULT NULL,
    INDEX `idx_vehicle_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Production Orders Table
CREATE TABLE `production_orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `vehicle_id` INT NOT NULL,
    `progress_percentage` INT NOT NULL DEFAULT 0,
    `start_date` DATE DEFAULT NULL,
    `estimated_completion_date` DATE DEFAULT NULL,
    `status` VARCHAR(50) NOT NULL DEFAULT 'Planned', -- Planned, In Progress, Quality Check, Completed, Delayed
    FOREIGN KEY (`vehicle_id`) REFERENCES `vehicles`(`id`) ON DELETE CASCADE,
    INDEX `idx_order_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Employees Table
CREATE TABLE `employees` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `department` VARCHAR(100) NOT NULL, -- Assembly, Quality Assurance, Logistics, Engineering
    `role` VARCHAR(100) NOT NULL -- Technician, QA Inspector, Supervisor, Line Manager
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Tasks Table
CREATE TABLE `tasks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `employee_id` INT DEFAULT NULL,
    `description` TEXT NOT NULL,
    `status` VARCHAR(50) NOT NULL DEFAULT 'Pending', -- Pending, In Progress, Completed
    FOREIGN KEY (`employee_id`) REFERENCES `employees`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Reports Table
CREATE TABLE `reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `report_type` VARCHAR(100) NOT NULL, -- Vehicle Production, Employee Performance, Production Efficiency
    `generated_by` INT DEFAULT NULL,
    `generated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `data_summary` TEXT NOT NULL,
    FOREIGN KEY (`generated_by`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Activity Logs Table
CREATE TABLE `activity_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT DEFAULT NULL,
    `action` VARCHAR(255) NOT NULL,
    `details` TEXT DEFAULT NULL,
    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_log_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert Seed Data

-- Roles
INSERT INTO `roles` (`id`, `name`) VALUES
(1, 'Administrator'),
(2, 'Production Manager'),
(3, 'Operations Staff');

-- Users
-- Password for admin is 'admin123'
-- Password for manager is 'manager123'
-- Password for staff is 'staff123'
INSERT INTO `users` (`id`, `username`, `password_hash`, `role_id`) VALUES
(1, 'admin', 'scrypt:32768:8:1$Yu6IyriUmPBsD49i$68585d66b4e93377127da81eec595b32eb9df54eb39d35d4f2c3b48cfb24ca143455d97e905b2932539d6084f15bc6e072620950080d39c6ad639bab356ec412', 1),
(2, 'manager', 'scrypt:32768:8:1$ksIiJVadRjvbvBsG$f7d18636b3d02bfa5e3ceb183d396e2409f58ac46453f14f4d65a138b4dcf7fa9c57f21ab6609d30aecaf7cba1a4325b3701d85f7100c547b8d1141c82a0ed30', 2),
(3, 'staff', 'scrypt:32768:8:1$hsyhOdxFIo7ZElSh$a76d838875ab47db1b7a11d87ff541e1be1feae83e01afb2d41add7d5ef1de99ec6fab6a179d61cd8409d32569366bf98239f8d9b43ce3def39a9d890652c794', 3);

-- Vehicles (for production data)
INSERT INTO `vehicles` (`id`, `model`, `type`, `assembly_line`, `status`, `start_date`, `completion_date`) VALUES
(1, 'CyberTruck Zenith', 'Electric', 'Line Alpha (EV)', 'Completed', '2026-05-10', '2026-05-18'),
(2, 'CyberTruck Zenith', 'Electric', 'Line Alpha (EV)', 'Completed', '2026-05-12', '2026-05-20'),
(3, 'Model Horizon S', 'Sedan', 'Line Beta (Sedan)', 'Completed', '2026-05-14', '2026-05-22'),
(4, 'Triton Pickup', 'Truck', 'Line Gamma (HD)', 'In Progress', '2026-06-01', NULL),
(5, 'Apex SUV EV', 'Electric', 'Line Alpha (EV)', 'Quality Check', '2026-06-02', NULL),
(6, 'Model Horizon S', 'Sedan', 'Line Beta (Sedan)', 'Delayed', '2026-06-01', NULL),
(7, 'Phoenix Roadster', 'Electric', 'Line Alpha (EV)', 'Planned', NULL, NULL),
(8, 'Triton Pickup', 'Truck', 'Line Gamma (HD)', 'Planned', NULL, NULL),
(9, 'Apex SUV EV', 'Electric', 'Line Alpha (EV)', 'Completed', '2026-05-20', '2026-05-29'),
(10, 'Triton Pickup', 'Truck', 'Line Gamma (HD)', 'Completed', '2026-05-18', '2026-05-27');

-- Production Orders
INSERT INTO `production_orders` (`id`, `vehicle_id`, `progress_percentage`, `start_date`, `estimated_completion_date`, `status`) VALUES
(1, 1, 100, '2026-05-10', '2026-05-18', 'Completed'),
(2, 2, 100, '2026-05-12', '2026-05-20', 'Completed'),
(3, 3, 100, '2026-05-14', '2026-05-22', 'Completed'),
(4, 4, 65, '2026-06-01', '2026-06-18', 'In Progress'),
(5, 5, 90, '2026-06-02', '2026-06-12', 'Quality Check'),
(6, 6, 40, '2026-06-01', '2026-06-10', 'Delayed'),
(7, 7, 0, NULL, '2026-06-25', 'Planned'),
(8, 8, 0, NULL, '2026-06-30', 'Planned'),
(9, 9, 100, '2026-05-20', '2026-05-29', 'Completed'),
(10, 10, 100, '2026-05-18', '2026-05-27', 'Completed');

-- Employees
INSERT INTO `employees` (`id`, `name`, `department`, `role`) VALUES
(1, 'Ritesh', 'Assembly', 'Technician'),
(2, 'Atharva', 'Assembly', 'Technician'),
(3, 'Anand', 'Engineering', 'Supervisor'),
(4, 'Rizwan', 'Quality Assurance', 'QA Inspector'),
(5, 'Sarthak', 'Logistics', 'Line Manager');

-- Tasks
INSERT INTO `tasks` (`id`, `employee_id`, `description`, `status`) VALUES
(1, 1, 'Install battery cell module in CyberTruck Zenith #4', 'In Progress'),
(2, 2, 'Assemble interior dashboard panel on Model Horizon S #6', 'In Progress'),
(3, 3, 'Calibrate Line Alpha robotic arms calibration software', 'Completed'),
(4, 4, 'Conduct paint depth quality inspection on Apex SUV EV #5', 'Pending'),
(5, 5, 'Coordinate logistics for Triton Pickup heavy chassis delivery', 'Completed');

-- Reports (Sample logged actions)
INSERT INTO `reports` (`id`, `report_type`, `generated_by`, `generated_at`, `data_summary`) VALUES
(1, 'Vehicle Production', 2, '2026-05-30 14:30:00', 'Total Vehicles Produced in May: 5. Focus Line Alpha EV.'),
(2, 'Production Efficiency', 2, '2026-06-01 09:15:00', 'Average assembly time: 8.2 days. Bottleneck identified in Line Beta upholstery assembly.');

-- Activity Logs
INSERT INTO `activity_logs` (`id`, `user_id`, `action`, `details`, `timestamp`) VALUES
(1, 1, 'User Login', 'Admin user logged in from IP ::1', '2026-06-15 10:00:00'),
(2, 2, 'User Login', 'Manager user logged in from IP ::1', '2026-06-15 10:05:00'),
(3, 2, 'Vehicle Creation', 'Created vehicle CyberTruck Zenith (ID: 7)', '2026-06-15 10:15:00'),
(4, 2, 'Production Updates', 'Updated progress for Triton Pickup to 65%', '2026-06-15 10:20:00'),
(5, 3, 'User Login', 'Staff user logged in from IP ::1', '2026-06-15 10:30:00');
