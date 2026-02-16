-- Create expenses table
CREATE TABLE IF NOT EXISTS expenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    category TEXT NOT NULL, -- 'Infrastructure', 'Plantation', 'Travel', etc.
    phase INTEGER NOT NULL, -- 1, 2, 3
    date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Update fund_metrics table if it exists, or create if not. 
-- Assuming fund_metrics exists with total_fund_value. We add total_expenses.
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'total_expenses') THEN
        ALTER TABLE fund_metrics ADD COLUMN total_expenses NUMERIC DEFAULT 0;
    END IF;
END $$;
