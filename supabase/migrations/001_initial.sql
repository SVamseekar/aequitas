-- Aequitas initial schema
-- Run via: supabase db push  OR  paste into Supabase SQL editor

-- -----------------------------------------------------------------------
-- Profiles (auto-created on signup via trigger)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    bio TEXT,
    policy_interests TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own profile"   ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- -----------------------------------------------------------------------
-- Conversations
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.conversations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title      TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own conversations" ON public.conversations
    FOR ALL USING (auth.uid() = user_id);

-- -----------------------------------------------------------------------
-- Messages
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.messages (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id   UUID REFERENCES public.conversations(id) ON DELETE CASCADE NOT NULL,
    user_id           UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    role              TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content           TEXT NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own messages" ON public.messages
    FOR ALL USING (auth.uid() = user_id);

-- -----------------------------------------------------------------------
-- Saved analyses (bookmarked narratives / chat responses)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.saved_analyses (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title      TEXT NOT NULL,
    content    TEXT NOT NULL,
    section_id TEXT,
    dimension  TEXT,
    tags       TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.saved_analyses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own saved analyses" ON public.saved_analyses
    FOR ALL USING (auth.uid() = user_id);

-- -----------------------------------------------------------------------
-- Policy notes (journal-style per dimension)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.policy_notes (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    dimension  TEXT NOT NULL,
    region     TEXT DEFAULT 'all',
    stance     TEXT CHECK (stance IN ('priority', 'monitor', 'adequate')),
    thesis     TEXT NOT NULL,
    critique   TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.policy_notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own policy notes" ON public.policy_notes
    FOR ALL USING (auth.uid() = user_id);

-- -----------------------------------------------------------------------
-- Saved regions (tracked regions watchlist)
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.saved_regions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    region_code TEXT NOT NULL,
    region_name TEXT NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.saved_regions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can CRUD own saved regions" ON public.saved_regions
    FOR ALL USING (auth.uid() = user_id);
