-- consolidated_migration.sql
-- Run this in Supabase SQL Editor to prepare for Multi-Fund Institutional Dashboard

-- 1. Ensure UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Add fund_id to tables that missed it
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'activity_log' AND column_name = 'fund_id') THEN
        ALTER TABLE activity_log ADD COLUMN fund_id UUID REFERENCES funds(id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'investments' AND column_name = 'fund_id') THEN
        ALTER TABLE investments ADD COLUMN fund_id UUID REFERENCES funds(id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'expenses' AND column_name = 'fund_id') THEN
        ALTER TABLE expenses ADD COLUMN fund_id UUID REFERENCES funds(id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_performance_history' AND column_name = 'fund_id') THEN
        ALTER TABLE fund_performance_history ADD COLUMN fund_id UUID REFERENCES funds(id);
    END IF;
END $$;

-- 3. Add missing columns to fund_metrics for the premium charts
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'total_fund_value') THEN
        ALTER TABLE fund_metrics ADD COLUMN total_fund_value NUMERIC DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'stock_price') THEN
        ALTER TABLE fund_metrics ADD COLUMN stock_price INTEGER DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'land_value') THEN
        ALTER TABLE fund_metrics ADD COLUMN land_value NUMERIC DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'total_profits') THEN
        ALTER TABLE fund_metrics ADD COLUMN total_profits NUMERIC DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'total_expenses') THEN
        ALTER TABLE fund_metrics ADD COLUMN total_expenses NUMERIC DEFAULT 0;
    END IF;
END $$;

-- 4. Create default fund if none exists and link records
INSERT INTO funds (id, name, location, operational_status, target_amount)
SELECT 'd290f1ee-6c54-4b01-90e6-d701748f0851', 'Golden Mango Grove', 'Chittoor, AP', 'Active', 26500000
WHERE NOT EXISTS (SELECT 1 FROM funds WHERE id = 'd290f1ee-6c54-4b01-90e6-d701748f0851');

DO $$
DECLARE
    default_fund_id UUID := 'd290f1ee-6c54-4b01-90e6-d701748f0851';
BEGIN
    UPDATE activity_log SET fund_id = default_fund_id WHERE fund_id IS NULL;
    UPDATE investments SET fund_id = default_fund_id WHERE fund_id IS NULL;
    UPDATE expenses SET fund_id = default_fund_id WHERE fund_id IS NULL;
    UPDATE fund_performance_history SET fund_id = default_fund_id WHERE fund_id IS NULL;
    UPDATE fund_metrics SET fund_id = default_fund_id WHERE fund_id IS NULL;
END $$;

-- 5. Seed initial metrics for the default fund if not present
INSERT INTO fund_metrics (fund_id, total_fund_value, stock_price, total_stocks, growth_percentage, phase1_progress, phase2_progress, phase3_progress)
SELECT 'd290f1ee-6c54-4b01-90e6-d701748f0851', 26500000, 26500, 1000, 12.5, 85, 40, 15
WHERE NOT EXISTS (SELECT 1 FROM fund_metrics WHERE fund_id = 'd290f1ee-6c54-4b01-90e6-d701748f0851');
