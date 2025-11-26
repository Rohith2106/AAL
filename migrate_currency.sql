-- Migration: Add currency support to ledger_entries table
-- Run this SQL script in your MySQL database

-- Add currency column (ISO code like USD, IDR, ZAR)
ALTER TABLE ledger_entries 
ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'USD' AFTER total;

-- Add exchange_rate column (rate to convert to USD)
ALTER TABLE ledger_entries 
ADD COLUMN IF NOT EXISTS exchange_rate FLOAT DEFAULT 1.0 AFTER currency;

-- Add usd_total column (total amount in USD for aggregation)
ALTER TABLE ledger_entries 
ADD COLUMN IF NOT EXISTS usd_total FLOAT AFTER exchange_rate;

-- Update existing records to set usd_total = total (assuming they're USD)
UPDATE ledger_entries 
SET usd_total = total 
WHERE usd_total IS NULL;

-- Verify the migration
SELECT COUNT(*) as total_records, 
       SUM(CASE WHEN currency IS NOT NULL THEN 1 ELSE 0 END) as records_with_currency
FROM ledger_entries;
