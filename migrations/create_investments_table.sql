-- Create investments table to track purchase history
CREATE TABLE IF NOT EXISTS investments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT REFERENCES profiles(email),
    stock_count INTEGER NOT NULL,
    amount_paid NUMERIC NOT NULL,
    status TEXT DEFAULT 'completed', -- 'pending', 'completed', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add total_stocks column to profiles to keep a cumulative balance
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'profiles' AND column_name = 'total_stocks') THEN
        ALTER TABLE profiles ADD COLUMN total_stocks INTEGER DEFAULT 0;
    END IF;
END $$;
