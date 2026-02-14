-- SmIA Database Schema
-- Applied to Supabase project: fueryelktpkkwipwyswu
-- Date: 2026-02-13

-- Table: user_bindings
CREATE TABLE public.user_bindings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  telegram_user_id BIGINT UNIQUE NOT NULL,
  bind_code VARCHAR(6),
  code_expires_at TIMESTAMPTZ,
  bound_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, telegram_user_id)
);

CREATE INDEX idx_bindings_telegram_user ON public.user_bindings(telegram_user_id);
CREATE INDEX idx_bindings_user ON public.user_bindings(user_id);

ALTER TABLE public.user_bindings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own bindings"
  ON public.user_bindings
  FOR ALL
  USING (auth.uid() = user_id);

-- Table: analysis_reports
CREATE TABLE public.analysis_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  query TEXT NOT NULL,
  topic VARCHAR(500),
  sentiment VARCHAR(20) CHECK (sentiment IN ('Positive', 'Negative', 'Neutral')),
  sentiment_score NUMERIC(3, 2) CHECK (sentiment_score >= 0 AND sentiment_score <= 1),
  summary TEXT NOT NULL,
  key_insights JSONB NOT NULL DEFAULT '[]',
  top_discussions JSONB NOT NULL DEFAULT '[]',
  keywords JSONB NOT NULL DEFAULT '[]',
  source_breakdown JSONB NOT NULL DEFAULT '{}',
  charts_data JSONB,
  source VARCHAR(20) CHECK (source IN ('web', 'telegram')) NOT NULL,
  processing_time_seconds INTEGER,
  langfuse_trace_id VARCHAR(255),
  token_usage JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reports_user ON public.analysis_reports(user_id);
CREATE INDEX idx_reports_created ON public.analysis_reports(created_at DESC);
CREATE INDEX idx_reports_sentiment ON public.analysis_reports(sentiment);
CREATE INDEX idx_reports_query ON public.analysis_reports USING GIN (to_tsvector('english', query));

ALTER TABLE public.analysis_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own reports"
  ON public.analysis_reports
  FOR ALL
  USING (auth.uid() = user_id);
