CREATE TABLE IF NOT EXISTS Inventory (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    on_hand_units INTEGER NOT NULL,
    safety_stock_units INTEGER NOT NULL,
    holding_cost_per_unit_year REAL NOT NULL,
    setup_cost_per_order REAL NOT NULL,
    unit_cost REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS Supplier (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    otif_rate REAL NOT NULL,
    defect_rate REAL NOT NULL,
    lead_time_days INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    moq INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS Sales_Forecast (
    sku TEXT NOT NULL,
    week_ahead INTEGER NOT NULL,
    mean_demand REAL NOT NULL,
    std_dev REAL NOT NULL,
    PRIMARY KEY (sku, week_ahead)
);

INSERT OR REPLACE INTO Inventory VALUES
('SKU-A21', 'Industrial Coupling A21', 4200, 900, 1.8, 55, 12.4),
('SKU-B11', 'Valve B11', 2800, 700, 1.4, 48, 9.8),
('SKU-C07', 'Bearing C07', 3600, 800, 2.1, 62, 15.3);

INSERT OR REPLACE INTO Supplier VALUES
('SUP-LOCAL-01', 'LocalPrime', 'local', 0.96, 0.012, 5, 14.1, 300),
('SUP-SEA-03', 'SeaBridge', 'sea', 0.86, 0.026, 24, 10.2, 800),
('SUP-EU-02', 'EuroParts', 'eu', 0.92, 0.017, 15, 12.8, 500),
('SUP-US-04', 'USMFG', 'us', 0.90, 0.016, 18, 13.2, 450),
('SUP-SEA-05', 'BlueHarbor', 'sea', 0.88, 0.021, 21, 10.8, 700);

INSERT OR REPLACE INTO Sales_Forecast VALUES
('SKU-A21', 1, 1300, 260),
('SKU-A21', 2, 1250, 280),
('SKU-A21', 3, 1180, 250),
('SKU-B11', 1, 920, 180),
('SKU-B11', 2, 960, 210),
('SKU-B11', 3, 900, 170),
('SKU-C07', 1, 1040, 220),
('SKU-C07', 2, 1010, 205),
('SKU-C07', 3, 980, 190);

