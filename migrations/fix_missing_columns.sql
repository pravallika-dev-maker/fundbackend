-- Add total_stocks column to profiles if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'profiles' AND column_name = 'total_stocks') THEN
        ALTER TABLE profiles ADD COLUMN total_stocks INTEGER DEFAULT 0;
    END IF;
END $$;

-- Ensure is_investor column exists (should be there, but check)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'profiles' AND column_name = 'is_investor') THEN
        ALTER TABLE profiles ADD COLUMN is_investor BOOLEAN DEFAULT FALSE;
    END IF;
END $$;
