-- Migration to add fund_id to all relevant tables for multi-fund support

-- 1. fund_metrics
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'fund_id') THEN
        ALTER TABLE fund_metrics ADD COLUMN fund_id UUID REFERENCES funds(id);
    END IF;
END $$;

-- 2. investments
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'investments' AND column_name = 'fund_id') THEN
        ALTER TABLE investments ADD COLUMN fund_id UUID REFERENCES funds(id);
    END IF;
END $$;

-- 3. activity_log
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'activity_log' AND column_name = 'fund_id') THEN
        ALTER TABLE activity_log ADD COLUMN fund_id UUID REFERENCES funds(id);
    END IF;
END $$;

-- 4. expenses
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'expenses' AND column_name = 'fund_id') THEN
        ALTER TABLE expenses ADD COLUMN fund_id UUID REFERENCES funds(id);
    END IF;
END $$;

-- 5. fund_performance_history
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_performance_history' AND column_name = 'fund_id') THEN
        ALTER TABLE fund_performance_history ADD COLUMN fund_id UUID REFERENCES funds(id);
    END IF;
END $$;

-- 6. fund_allocation
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_allocation' AND column_name = 'fund_id') THEN
        ALTER TABLE fund_allocation ADD COLUMN fund_id UUID REFERENCES funds(id);
    END IF;
END $$;

-- Create a default fund if none exists to link old records
INSERT INTO funds (name, location, status, total_target_capital)
SELECT 'Vriksha Heritage Farm', 'Coimbatore, TN', 'Active', 26500000
WHERE NOT EXISTS (SELECT 1 FROM funds);

-- Link existing records to the default fund (assuming the one we just created or the only one)
DO $$
DECLARE
    default_fund_id UUID;
BEGIN
    SELECT id INTO default_fund_id FROM funds LIMIT 1;
    
    UPDATE fund_metrics SET fund_id = default_fund_id WHERE fund_id IS NULL;
    UPDATE investments SET fund_id = default_fund_id WHERE fund_id IS NULL;
    UPDATE activity_log SET fund_id = default_fund_id WHERE fund_id IS NULL;
    UPDATE expenses SET fund_id = default_fund_id WHERE fund_id IS NULL;
    UPDATE fund_performance_history SET fund_id = default_fund_id WHERE fund_id IS NULL;
    UPDATE fund_allocation SET fund_id = default_fund_id WHERE fund_id IS NULL;
END $$;
