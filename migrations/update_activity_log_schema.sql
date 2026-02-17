-- Ensure activity_log has category and phase columns for detailed expense tracking
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'activity_log' AND column_name = 'category') THEN
        ALTER TABLE activity_log ADD COLUMN category TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'activity_log' AND column_name = 'phase') THEN
        ALTER TABLE activity_log ADD COLUMN phase INTEGER;
    END IF;
END $$;
