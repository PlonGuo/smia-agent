-- Migration: Add AI Daily Digest tables, RPC functions, RLS policies, and indexes
-- Run this against your Supabase project via Supabase MCP or SQL Editor

-- ============================================================
-- 1. TABLES
-- ============================================================

-- Daily digest reports (one per day)
CREATE TABLE public.daily_digests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  digest_date DATE NOT NULL UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'collecting'
    CHECK (status IN ('collecting', 'analyzing', 'completed', 'failed')),
  executive_summary TEXT,
  items JSONB DEFAULT '[]'::jsonb,
  top_highlights JSONB DEFAULT '[]'::jsonb,
  trending_keywords JSONB DEFAULT '[]'::jsonb,
  category_counts JSONB DEFAULT '{}'::jsonb,
  source_counts JSONB DEFAULT '{}'::jsonb,
  source_health JSONB DEFAULT '{}'::jsonb,
  total_items INTEGER DEFAULT 0,
  model_used VARCHAR(100),
  processing_time_seconds INTEGER,
  langfuse_trace_id VARCHAR(255),
  token_usage JSONB,
  prompt_version VARCHAR(50),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_daily_digests_status ON daily_digests(status);

-- Collector cache (per source per day, for smart retry)
CREATE TABLE public.digest_collector_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  digest_date DATE NOT NULL,
  source VARCHAR(50) NOT NULL,
  items JSONB NOT NULL DEFAULT '[]'::jsonb,
  item_count INTEGER DEFAULT 0,
  collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(digest_date, source)
);

-- Admin users
CREATE TABLE public.admins (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Authorized digest users (approved by admin)
CREATE TABLE public.digest_authorized_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL UNIQUE,
  approved_by UUID REFERENCES admins(user_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Access requests
CREATE TABLE public.digest_access_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  reason TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'rejected')),
  rejection_reason TEXT,
  reviewed_by UUID,
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_digest_access_requests_user_id ON digest_access_requests(user_id);
CREATE INDEX idx_digest_access_requests_status ON digest_access_requests(status);

-- Bookmarks
CREATE TABLE public.digest_bookmarks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  digest_id UUID NOT NULL REFERENCES daily_digests(id) ON DELETE CASCADE,
  item_url TEXT NOT NULL,
  item_title TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, item_url)
);

-- Feedback (thumbs up/down)
CREATE TABLE public.digest_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  digest_id UUID NOT NULL REFERENCES daily_digests(id) ON DELETE CASCADE,
  item_url TEXT,
  vote SMALLINT NOT NULL CHECK (vote IN (1, -1)),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, digest_id, item_url)
);

-- Share tokens
CREATE TABLE public.digest_share_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  digest_id UUID NOT NULL REFERENCES daily_digests(id) ON DELETE CASCADE,
  token VARCHAR(64) NOT NULL UNIQUE,
  created_by UUID REFERENCES auth.users(id),
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 2. RLS POLICIES
-- ============================================================

-- daily_digests: authenticated can SELECT completed, service role can ALL
ALTER TABLE daily_digests ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated users can view completed digests"
  ON daily_digests FOR SELECT TO authenticated
  USING (status = 'completed');
CREATE POLICY "Service role full access on daily_digests"
  ON daily_digests FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- digest_collector_cache: service role only
ALTER TABLE digest_collector_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on digest_collector_cache"
  ON digest_collector_cache FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- admins: service role can ALL, authenticated can SELECT own row
ALTER TABLE admins ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated users can view own admin row"
  ON admins FOR SELECT TO authenticated
  USING (user_id = auth.uid());
CREATE POLICY "Service role full access on admins"
  ON admins FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- digest_authorized_users: service role can ALL, authenticated can SELECT own row
ALTER TABLE digest_authorized_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated users can view own authorized row"
  ON digest_authorized_users FOR SELECT TO authenticated
  USING (user_id = auth.uid());
CREATE POLICY "Service role full access on digest_authorized_users"
  ON digest_authorized_users FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- digest_access_requests: service role can ALL, authenticated can INSERT own + SELECT own
ALTER TABLE digest_access_requests ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own access requests"
  ON digest_access_requests FOR SELECT TO authenticated
  USING (user_id = auth.uid());
CREATE POLICY "Users can create own access requests"
  ON digest_access_requests FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());
CREATE POLICY "Service role full access on digest_access_requests"
  ON digest_access_requests FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- digest_bookmarks: users can CRUD own rows
ALTER TABLE digest_bookmarks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own bookmarks"
  ON digest_bookmarks FOR ALL TO authenticated
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "Service role full access on digest_bookmarks"
  ON digest_bookmarks FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- digest_feedback: users can CRUD own rows
ALTER TABLE digest_feedback ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own feedback"
  ON digest_feedback FOR ALL TO authenticated
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY "Service role full access on digest_feedback"
  ON digest_feedback FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- digest_share_tokens: service role can ALL
ALTER TABLE digest_share_tokens ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on digest_share_tokens"
  ON digest_share_tokens FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- ============================================================
-- 3. RPC FUNCTIONS
-- ============================================================

-- Atomic digest generation claim (race condition safe)
-- Returns JSONB for predictable PostgREST serialization (C3)
CREATE OR REPLACE FUNCTION claim_digest_generation(p_date DATE)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE v_id UUID; v_status TEXT;
BEGIN
    -- 1. Reclaim stale locks (crashed generators, 150s timeout)
    UPDATE daily_digests SET status = 'failed', updated_at = NOW()
    WHERE digest_date = p_date
      AND status IN ('collecting', 'analyzing')
      AND updated_at < NOW() - INTERVAL '150 seconds';

    -- 2. Atomic claim: insert OR reclaim failed (single SQL operation)
    INSERT INTO daily_digests (digest_date, status, updated_at)
    VALUES (p_date, 'collecting', NOW())
    ON CONFLICT (digest_date) DO UPDATE
      SET status = 'collecting', updated_at = NOW()
      WHERE daily_digests.status = 'failed'
    RETURNING id INTO v_id;

    -- 3. Did we win?
    IF v_id IS NOT NULL THEN
        RETURN jsonb_build_object('claimed', true, 'digest_id', v_id, 'current_status', 'collecting');
    ELSE
        SELECT d.id, d.status INTO v_id, v_status
        FROM daily_digests d WHERE d.digest_date = p_date;
        RETURN jsonb_build_object('claimed', false, 'digest_id', v_id, 'current_status', v_status);
    END IF;
END;
$$;

-- Seed first admin from email (bootstrap, idempotent)
CREATE OR REPLACE FUNCTION seed_admin(p_email TEXT)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO admins (user_id, email)
    SELECT id, email FROM auth.users WHERE email = p_email
    ON CONFLICT (email) DO NOTHING;
END;
$$;
