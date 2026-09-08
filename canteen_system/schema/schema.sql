CREATE DATABASE IF NOT EXISTS canteen_db;
USE canteen_db;

CREATE TABLE IF NOT EXISTS Customers (
    CustomerID INT AUTO_INCREMENT PRIMARY KEY,
    FullName VARCHAR(100) NOT NULL,
    CustomerType ENUM('Student', 'Staff') NOT NULL,
    ContactNumber VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS Management (
    ManagerID INT AUTO_INCREMENT PRIMARY KEY,
    FullName VARCHAR(100) NOT NULL,
    AccessLevel ENUM('Manager', 'Admin') NOT NULL,
    ContactNumber VARCHAR(20),
    Username VARCHAR(50) UNIQUE NOT NULL,
    PasswordHash VARCHAR(256) NOT NULL
);

CREATE TABLE IF NOT EXISTS MenuItems (
    ItemID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Category VARCHAR(50),
    CostPrice DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS Inventory (
    IngredientID INT AUTO_INCREMENT PRIMARY KEY,
    IngredientName VARCHAR(100) NOT NULL,
    CurrentStockQuantity DECIMAL(10, 2) NOT NULL,
    ReorderThreshold DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS MenuIngredients (
    ItemID INT,
    IngredientID INT,
    QuantityRequired DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (ItemID, IngredientID),
    FOREIGN KEY (ItemID) REFERENCES MenuItems(ItemID),
    FOREIGN KEY (IngredientID) REFERENCES Inventory(IngredientID)
);

CREATE TABLE IF NOT EXISTS DailyMenu (
    MenuDate DATE,
    ItemID INT,
    QuantityPrepared INT NOT NULL DEFAULT 0,
    QuantitySold INT NOT NULL DEFAULT 0,
    PRIMARY KEY (MenuDate, ItemID),
    FOREIGN KEY (ItemID) REFERENCES MenuItems(ItemID)
);

CREATE TABLE IF NOT EXISTS Orders (
    OrderID INT AUTO_INCREMENT PRIMARY KEY,
    CustomerID INT,
    ItemID INT,
    OrderTimestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    QuantityOrdered INT NOT NULL,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (ItemID) REFERENCES MenuItems(ItemID)
);

CREATE TABLE IF NOT EXISTS WastageLog (
    LogID INT AUTO_INCREMENT PRIMARY KEY,
    LogDate DATE NOT NULL,
    ItemID INT,
    QuantityWasted INT NOT NULL,
    FOREIGN KEY (ItemID) REFERENCES MenuItems(ItemID)
);

CREATE TABLE IF NOT EXISTS Alerts (
    AlertID INT AUTO_INCREMENT PRIMARY KEY,
    IngredientID INT,
    AlertTimestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    AlertType VARCHAR(50) NOT NULL,
    FOREIGN KEY (IngredientID) REFERENCES Inventory(IngredientID)
);

-- Trigger for Low-Stock Alerts
DELIMITER //

DROP TRIGGER IF EXISTS LowStockAlert //

CREATE TRIGGER LowStockAlert
AFTER UPDATE ON Inventory
FOR EACH ROW
BEGIN
    IF NEW.CurrentStockQuantity <= NEW.ReorderThreshold AND OLD.CurrentStockQuantity > NEW.ReorderThreshold THEN
        INSERT INTO Alerts (IngredientID, AlertType)
        VALUES (NEW.IngredientID, 'Low Stock Warning');
    END IF;
END //

DELIMITER ;
