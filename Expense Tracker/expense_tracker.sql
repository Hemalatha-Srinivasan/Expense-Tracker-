CREATE DATABASE expense_tracker;
USE expense_tracker;
CREATE TABLE expenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(255),
    amount DECIMAL(10,2),
    date DATE,
    notes TEXT
);

SELECT * FROM expenses;

SELECT category, amount, date, notes FROM expenses WHERE MONTH(date) = MONTH(CURDATE());

SELECT category, SUM(amount) AS total_amount
FROM expenses
WHERE MONTH(date) = MONTH(CURDATE())
  AND YEAR(date) = YEAR(CURDATE())
GROUP BY category;

DELETE FROM expenses WHERE id = 1;

TRUNCATE TABLE expenses;
