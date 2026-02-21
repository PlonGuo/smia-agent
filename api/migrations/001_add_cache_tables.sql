-- Migration: Add caching tables for fetched data and analysis results
-- Run this against your Supabase project (SQL Editor)

-- Tier 1: Raw crawler output per source
CREATE TABLE public.fetch_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_normalized TEXT NOT NULL,
  time_range TEXT NOT NULL CHECK (time_range IN ('day', 'week', 'month', 'year')),
  source TEXT NOT NULL CHECK (source IN ('reddit', 'youtube', 'amazon')),
  data JSONB NOT NULL,
  item_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  UNIQUE(query_normalized, time_range, source)
);

CREATE INDEX idx_fetch_cache_lookup ON fetch_cache(query_normalized, time_range, source);
CREATE INDEX idx_fetch_cache_expires ON fetch_cache(expires_at);

-- Tier 2: Cached TrendReport for identical queries
CREATE TABLE public.analysis_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_normalized TEXT NOT NULL,
  time_range TEXT NOT NULL CHECK (time_range IN ('day', 'week', 'month', 'year')),
  report JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  UNIQUE(query_normalized, time_range)
);

CREATE INDEX idx_analysis_cache_lookup ON analysis_cache(query_normalized, time_range);
CREATE INDEX idx_analysis_cache_expires ON analysis_cache(expires_at);

-- No RLS needed — both tables store shared public data, accessed via service-role key only.
