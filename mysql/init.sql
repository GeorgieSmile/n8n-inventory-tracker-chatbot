-- =================================================================
--  1. CREATE TABLES
-- =================================================================

CREATE TABLE category(
	category_id INT AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(100) NOT NULL UNIQUE
);


CREATE TABLE product(
	product_id INT AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(150) NOT NULL,
	category_id INT NULL,
	sku VARCHAR(64) NULL UNIQUE,
	price DECIMAL(10,2) NOT NULL,
	reorder_level INT NOT NULL DEFAULT 10,
	CONSTRAINT fk_product_cat FOREIGN KEY (category_id) 
		REFERENCES category(category_id)
		ON UPDATE CASCADE ON DELETE SET NULL,
	INDEX idx_product_cat (category_id),
	INDEX idx_product_name (name)	
);


CREATE TABLE sale(
	sale_id INT AUTO_INCREMENT PRIMARY KEY,
	sale_datetime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	total_amount DECIMAL(10,2) NOT NULL,
	payment_method ENUM('Cash','Card','QR') NOT NULL,
	notes VARCHAR(255) NULL,
	INDEX idx_sale_datetime (sale_datetime)
);

CREATE TABLE sale_item(
	sale_item_id INT AUTO_INCREMENT PRIMARY KEY,
	sale_id INT NOT NULL,
	product_id INT NOT NULL,
	quantity INT NOT NULL,
	unit_price DECIMAL(10,2) NOT NULL,
	discount DECIMAL(10,2) NOT NULL DEFAULT 0,
	CONSTRAINT fk_sale_item_sale FOREIGN KEY (sale_id)
		REFERENCES sale(sale_id)
		ON UPDATE CASCADE ON DELETE CASCADE,
	CONSTRAINT fk_sale_item_product FOREIGN KEY (product_id)
		REFERENCES product(product_id)
		ON UPDATE RESTRICT ON DELETE RESTRICT,
	INDEX idx_sale_item_sale (sale_id),
	INDEX idx_sale_item_product (product_id)
);


CREATE TABLE stock_in(
	stock_in_id INT AUTO_INCREMENT PRIMARY KEY,
	ref_no VARCHAR(64) NULL,
	stock_in_date DATE NOT NULL,
	total_cost DECIMAL(10,2) NOT NULL DEFAULT 0,
	notes VARCHAR(255) NULL,
	INDEX idx_stock_in_date (stock_in_date)
);

CREATE TABLE stock_in_item(
	stock_in_item_id INT AUTO_INCREMENT PRIMARY KEY,
	stock_in_id INT NOT NULL,
	product_id INT NOT NULL,
	quantity INT NOT NULL,
	unit_cost DECIMAL(10,2) NOT NULL,
	CONSTRAINT fk_stock_in_item_parent FOREIGN KEY (stock_in_id)
		REFERENCES stock_in(stock_in_id)
		ON UPDATE CASCADE ON DELETE CASCADE,
	CONSTRAINT fk_stock_in_item_product FOREIGN KEY (product_id)
		REFERENCES product(product_id)
		ON UPDATE RESTRICT ON DELETE RESTRICT,
	INDEX idx_stock_in_item_parent (stock_in_id),
	INDEX idx_stock_in_item_product (product_id)
);


CREATE TABLE inventory_movement (
    movement_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    movement_type ENUM('STOCK_IN', 'SALE', 'ADJUSTMENT', 'OPENING') NOT NULL,
    quantity INT NOT NULL, -- Positive for stock in, negative for stock out
    unit_cost DECIMAL(10, 2) NULL, -- Cost for stock-in/opening
    sale_price DECIMAL(10, 2) NULL, -- Price for sale
    movement_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    stock_in_item_id INT NULL,
    sale_item_id INT NULL,
    notes VARCHAR(255),
    CONSTRAINT fk_im_product FOREIGN KEY (product_id)
        REFERENCES product(product_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_im_stock_in_item FOREIGN KEY (stock_in_item_id)
        REFERENCES stock_in_item(stock_in_item_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_im_sale_item FOREIGN KEY (sale_item_id)
        REFERENCES sale_item(sale_item_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
	INDEX idx_im_product_date (product_id, movement_date)
);

-- =================================================================
--  VIEWS
-- =================================================================

-- View for current product stock levels
CREATE OR REPLACE VIEW v_product_stock AS
SELECT 
    p.product_id,
    p.name,
    p.price,
    p.reorder_level,
    c.name AS category_name,
    COALESCE(SUM(im.quantity), 0) AS stock_on_hand,
    CASE 
        WHEN COALESCE(SUM(im.quantity), 0) <= p.reorder_level 
        THEN 1 ELSE 0 
    END AS needs_restock
FROM product p
LEFT JOIN category c ON p.category_id = c.category_id
LEFT JOIN inventory_movement im ON p.product_id = im.product_id
GROUP BY p.product_id, p.name, p.price, p.reorder_level, c.name;

-- View for calculating profitability of each sale item
CREATE OR REPLACE VIEW v_profitability_report AS
SELECT 
    si.sale_item_id,
    s.sale_id,
    s.sale_datetime,
    p.product_id,
    p.name AS product_name,
    c.name AS category_name,
    si.quantity,
    si.unit_price,
    si.discount,
    -- 1. Calculate the total revenue from this specific line item
    (si.quantity * si.unit_price * (1 - si.discount)) AS total_revenue,
    -- 2. Calculate the weighted average cost of the product at the time of sale
    (SELECT SUM(im_cost.quantity * im_cost.unit_cost) / SUM(im_cost.quantity)
        FROM inventory_movement im_cost
        WHERE im_cost.product_id = si.product_id
          AND im_cost.movement_type IN ('STOCK_IN', 'OPENING')
          AND im_cost.movement_date <= s.sale_datetime
    ) AS average_cost_at_sale,
    -- 3. Calculate the total cost for the items sold in this line
    (si.quantity * ( 
    			SELECT SUM(im_cost.quantity * im_cost.unit_cost) / SUM(im_cost.quantity)
            FROM inventory_movement im_cost
            WHERE im_cost.product_id = si.product_id
              AND im_cost.movement_type IN ('STOCK_IN', 'OPENING')
              AND im_cost.movement_date <= s.sale_datetime
        )
    ) AS total_cogs,
    -- 4. Calculate the final profit for this line item
    (si.quantity * si.unit_price * (1 - si.discount)) - 
    (si.quantity * (
            SELECT SUM(im_cost.quantity * im_cost.unit_cost) / SUM(im_cost.quantity)
            FROM inventory_movement im_cost
            WHERE im_cost.product_id = si.product_id
              AND im_cost.movement_type IN ('STOCK_IN', 'OPENING')
              AND im_cost.movement_date <= s.sale_datetime
        )
    ) AS gross_profit
FROM sale_item si
JOIN sale s ON si.sale_id = s.sale_id
JOIN product p ON si.product_id = p.product_id
LEFT JOIN category c ON p.category_id = c.category_id;


-- =================================================================
--  2. INSERT DATA
-- =================================================================

INSERT INTO `category` (`category_id`, `name`) VALUES
(1, 'สมาร์ทโฟน'),
(2, 'แล็ปท็อป'),
(3, 'อุปกรณ์เครื่องเสียง'),
(4, 'อุปกรณ์สวมใส่'),
(5, 'อุปกรณ์เสริม');

-- สมาร์ทโฟน (Category ID: 1)
INSERT INTO `product` (`product_id`, `name`, `category_id`, `sku`, `price`, `reorder_level`) VALUES
(101, 'Apple iPhone 16 Pro', 1, 'APP-IP16P-256', 41900.00, 10),
(102, 'Samsung Galaxy S25 Ultra', 1, 'SAM-GS25U-256', 45900.00, 10),
(103, 'Google Pixel 9', 1, 'GOO-PIX9-128', 29900.00, 15);

-- แล็ปท็อป (Category ID: 2)
INSERT INTO `product` (`product_id`, `name`, `category_id`, `sku`, `price`, `reorder_level`) VALUES
(201, 'Apple MacBook Air M3', 2, 'APP-MBA-M3-13', 34900.00, 10),
(202, 'Dell XPS 15', 2, 'DEL-XPS15-OLED', 68500.00, 5),
(203, 'Lenovo Yoga Slim 7', 2, 'LEN-YGS7-14', 28900.00, 8);

-- อุปกรณ์เครื่องเสียง (Category ID: 3)
INSERT INTO `product` (`product_id`, `name`, `category_id`, `sku`, `price`, `reorder_level`) VALUES
(301, 'Sony WH-1000XM6', 3, 'SON-WHXM6-B', 14900.00, 12),
(302, 'Bose QuietComfort Ultra Headphones', 3, 'BOS-QCUH-S', 15500.00, 12),
(303, 'Sennheiser Momentum 4', 3, 'SEN-MOM4-W', 12900.00, 10);

-- อุปกรณ์สวมใส่ (Category ID: 4)
INSERT INTO `product` (`product_id`, `name`, `category_id`, `sku`, `price`, `reorder_level`) VALUES
(401, 'Apple Watch Series 10', 4, 'APP-AW10-45', 15900.00, 15),
(402, 'Samsung Galaxy Watch 7', 4, 'SAM-GW7-44', 11900.00, 15),
(403, 'Garmin Fenix 8', 4, 'GAR-FEN8-PRO', 29900.00, 8);

-- อุปกรณ์เสริม (Category ID: 5)
INSERT INTO `product` (`product_id`, `name`, `category_id`, `sku`, `price`, `reorder_level`) VALUES
(501, 'Anker 737 Power Bank', 5, 'ANK-PB737-140W', 2990.00, 20),
(502, 'Logitech MX Master 4S', 5, 'LOG-MXM4S-G', 3990.00, 25),
(503, 'Ugreen 100W GaN Charger', 5, 'UGR-GAN100-4P', 1890.00, 30);


-- Create the "Opening Stock" event
INSERT INTO `stock_in` (`stock_in_id`, `ref_no`, `stock_in_date`, `total_cost`, `notes`) VALUES
(1, 'STKIN-20250811-001', '2025-08-11 09:30:00', 0, 'Opening Stock for my shop');

-- Insert all the items belonging to the stock-in event above.
INSERT INTO `stock_in_item` (`stock_in_id`, `product_id`, `quantity`, `unit_cost`) VALUES
-- Smartphones
(1, 101, 20, 29500.00), -- Apple iPhone 16 Pro
(1, 102, 15, 33000.00), -- Samsung Galaxy S25 Ultra
(1, 103, 25, 21500.00), -- Google Pixel 9

-- Laptops
(1, 201, 15, 28000.00), -- Apple MacBook Air M3
(1, 202, 8,  55000.00), -- Dell XPS 15
(1, 203, 12, 22000.00), -- Lenovo Yoga Slim 7

-- Audio Devices
(1, 301, 30, 11500.00), -- Sony WH-1000XM6
(1, 302, 50, 6500.00), -- Bose QuietComfort Ultra Headphones
(1, 303, 25, 9800.00), -- Sennheiser Momentum 4

-- Wearables
(1, 401, 40, 12000.00), -- Apple Watch Series 10
(1, 402, 30, 8500.00), -- Samsung Galaxy Watch 7
(1, 403, 10, 24000.00), -- Garmin Fenix 8

-- Accessories
(1, 501, 100, 1800.00), -- Anker 737 Power Bank
(1, 502, 80, 2900.00), -- Logitech MX Master 4S
(1, 503, 150, 1100.00); -- Ugreen 100W GaN Charger

-- Create initial inventory movement records
INSERT INTO inventory_movement (product_id, movement_type, quantity, unit_cost, stock_in_item_id, movement_date)
SELECT sii.product_id, 'OPENING', sii.quantity, sii.unit_cost, sii.stock_in_item_id, si.stock_in_date
FROM stock_in_item sii
JOIN stock_in si ON si.stock_in_id = sii.stock_in_id;

-- =================================================================
--  3. CREATE TRIGGERS
-- =================================================================

DELIMITER //

-- Updates total_cost AND creates the inventory movement record.
CREATE TRIGGER trg_after_stock_in_item_insert
AFTER INSERT ON stock_in_item
FOR EACH ROW
BEGIN
    -- First, update the total cost on the parent table
    UPDATE stock_in
    SET total_cost = total_cost + (NEW.quantity * NEW.unit_cost)
    WHERE stock_in_id = NEW.stock_in_id;

	-- Second, create the corresponding inventory movement record
    INSERT INTO inventory_movement(product_id, movement_type, quantity, unit_cost, stock_in_item_id, movement_date)
    SELECT NEW.product_id, 'STOCK_IN', NEW.quantity, NEW.unit_cost, NEW.stock_in_item_id, si.stock_in_date
    FROM stock_in si WHERE si.stock_in_id = NEW.stock_in_id;
END//

-- Adjusts total_cost AND updates the inventory movement record.
CREATE TRIGGER trg_after_stock_in_item_update
AFTER UPDATE ON stock_in_item
FOR EACH ROW
BEGIN
    -- First, adjust the total cost using both OLD and NEW values
    UPDATE stock_in
    SET total_cost = total_cost - (OLD.quantity * OLD.unit_cost) + (NEW.quantity * NEW.unit_cost)
    WHERE stock_in_id = OLD.stock_in_id;

    -- Second, update the corresponding inventory movement record
    UPDATE inventory_movement im
    JOIN stock_in si ON si.stock_in_id = OLD.stock_in_id
    SET 
        im.quantity = NEW.quantity,
        im.unit_cost = NEW.unit_cost,
        im.product_id = NEW.product_id,
        im.movement_date = si.stock_in_date
    WHERE im.stock_in_item_id = OLD.stock_in_item_id;
END//

-- Adjusts total_cost AND deletes the inventory movement record.
CREATE TRIGGER trg_before_stock_in_item_delete
BEFORE DELETE ON stock_in_item
FOR EACH ROW
BEGIN
    -- First, subtract the item's cost from the parent's total
    UPDATE stock_in
    SET total_cost = total_cost - (OLD.quantity * OLD.unit_cost)
    WHERE stock_in_id = OLD.stock_in_id;

    -- Second, delete the corresponding inventory movement record
    DELETE FROM inventory_movement WHERE stock_in_item_id = OLD.stock_in_item_id;
END//

-- Creates inventory movement AND adjusts sale total_amount after insert.
CREATE TRIGGER trg_after_sale_item_insert
AFTER INSERT ON sale_item
FOR EACH ROW
BEGIN
  -- First, add the item's value to the sale's total_amount.
  UPDATE sale
  SET total_amount = total_amount + (NEW.quantity * NEW.unit_price * (1 - NEW.discount))
  WHERE sale_id = NEW.sale_id;

  -- Second, create the corresponding inventory movement record.
  INSERT INTO inventory_movement (product_id, movement_type, quantity, sale_price, sale_item_id, movement_date)
  SELECT NEW.product_id, 'SALE', -NEW.quantity, NEW.unit_price * (1 - NEW.discount), NEW.sale_item_id, s.sale_datetime
  FROM sale s WHERE s.sale_id = NEW.sale_id;
END//

-- Adjusts inventory movement AND sale total_amount after update.
CREATE TRIGGER trg_after_sale_item_update
AFTER UPDATE ON sale_item
FOR EACH ROW
BEGIN
  -- First, adjust the sale's total_amount using both OLD and NEW values.
  UPDATE sale
  SET total_amount = total_amount - (OLD.quantity * OLD.unit_price * (1 - OLD.discount)) + (NEW.quantity * NEW.unit_price * (1 - NEW.discount))
  WHERE sale_id = NEW.sale_id;

  -- Second, update the quantity in the corresponding inventory movement record.
  UPDATE inventory_movement im
  SET im.quantity = -NEW.quantity, im.sale_price = NEW.unit_price * (1 - NEW.discount), im.product_id = NEW.product_id
  WHERE sale_item_id = NEW.sale_item_id;
END//

-- Deletes inventory movement AND adjusts sale total_amount before delete.
CREATE TRIGGER trg_before_sale_item_delete
BEFORE DELETE ON sale_item
FOR EACH ROW
BEGIN
  -- First, subtract the item's value from the sale's total_amount.
  UPDATE sale
  SET total_amount = total_amount - (OLD.quantity * OLD.unit_price * (1 - OLD.discount))
  WHERE sale_id = OLD.sale_id;
  
  -- Second, delete the corresponding inventory movement record.
  DELETE FROM inventory_movement WHERE sale_item_id = OLD.sale_item_id;
END//

CREATE TRIGGER trg_before_sale_delete
BEFORE DELETE ON sale
FOR EACH ROW
BEGIN
  DELETE im
  FROM inventory_movement im
  JOIN sale_item si
    ON si.sale_item_id = im.sale_item_id
  WHERE si.sale_id = OLD.sale_id;
END//

DELIMITER ;