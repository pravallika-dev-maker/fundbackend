-- 0. Enable UUID extension (Required for Expenses table)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Fix Permissions for Fund Performance History (RLS)
-- This table stores BOTH 'Land Growth' and 'Profits' history
ALTER TABLE fund_performance_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Enable read access for all users" ON fund_performance_history;
CREATE POLICY "Enable read access for all users" ON fund_performance_history
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Enable insert access for all users" ON fund_performance_history;
CREATE POLICY "Enable insert access for all users" ON fund_performance_history
    FOR INSERT WITH CHECK (true);


-- 2. Ensure Fund Metrics Table has all required columns
DO $$
BEGIN
    -- Ensure total_stocks exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'total_stocks') THEN
        ALTER TABLE fund_metrics ADD COLUMN total_stocks INTEGER DEFAULT 1000;
    END IF;

    -- Ensure land_value exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'land_value') THEN
        ALTER TABLE fund_metrics ADD COLUMN land_value NUMERIC DEFAULT 0;
    END IF;

    -- Ensure total_profits exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'total_profits') THEN
        ALTER TABLE fund_metrics ADD COLUMN total_profits NUMERIC DEFAULT 0;
    END IF;

    -- Ensure total_expenses exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'total_expenses') THEN
        ALTER TABLE fund_metrics ADD COLUMN total_expenses NUMERIC DEFAULT 0;
    END IF;
    
    -- Ensure stock_price exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'stock_price') THEN
        ALTER TABLE fund_metrics ADD COLUMN stock_price INTEGER DEFAULT 0;
    END IF;

    -- Ensure total_fund_value exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'total_fund_value') THEN
        ALTER TABLE fund_metrics ADD COLUMN total_fund_value NUMERIC DEFAULT 0;
    END IF;
END $$;


-- 3. Ensure Expenses Table exists and has correct schema
CREATE TABLE IF NOT EXISTS expenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    category TEXT NOT NULL,
    phase INTEGER NOT NULL,
    date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for expenses (to be safe, allows insert if policy exists, or needs policy)
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;

-- Allow read access to expenses
DROP POLICY IF EXISTS "Enable read access for expenses" ON expenses;
CREATE POLICY "Enable read access for expenses" ON expenses
    FOR SELECT USING (true);

-- Allow insert access to expenses (for backend/admin)
DROP POLICY IF EXISTS "Enable insert access for expenses" ON expenses;
CREATE POLICY "Enable insert access for expenses" ON expenses
    FOR INSERT WITH CHECK (true);
