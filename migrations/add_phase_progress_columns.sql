-- Add phase progress columns to fund_metrics table
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'phase1_progress') THEN
        ALTER TABLE fund_metrics ADD COLUMN phase1_progress INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'phase2_progress') THEN
        ALTER TABLE fund_metrics ADD COLUMN phase2_progress INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'fund_metrics' AND column_name = 'phase3_progress') THEN
        ALTER TABLE fund_metrics ADD COLUMN phase3_progress INTEGER DEFAULT 0;
    END IF;
END $$;
