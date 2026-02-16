-- Add land_value and total_profits columns to fund_metrics table if they don't exist

DO $$ 
BEGIN 
    -- Add land_value column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'fund_metrics' AND column_name = 'land_value') THEN
        ALTER TABLE fund_metrics ADD COLUMN land_value NUMERIC DEFAULT 0;
        RAISE NOTICE 'Added land_value column to fund_metrics';
    END IF;
    
    -- Add total_profits column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'fund_metrics' AND column_name = 'total_profits') THEN
        ALTER TABLE fund_metrics ADD COLUMN total_profits NUMERIC DEFAULT 0;
        RAISE NOTICE 'Added total_profits column to fund_metrics';
    END IF;

    -- Add created_at column if it's missing (required for historical chart)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'fund_metrics' AND column_name = 'created_at') THEN
        ALTER TABLE fund_metrics ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        RAISE NOTICE 'Added created_at column to fund_metrics';
    END IF;
END $$;
