-- Migration 003: Add topic support to daily digests
-- Allows multiple digests per day (one per topic: ai, geopolitics, climate, health)

-- 1. Add topic column to daily_digests (default 'ai' for existing data)
ALTER TABLE daily_digests ADD COLUMN IF NOT EXISTS topic TEXT NOT NULL DEFAULT 'ai';

-- 2. Drop old unique constraint on digest_date, add composite unique (date + topic)
ALTER TABLE daily_digests DROP CONSTRAINT IF EXISTS daily_digests_digest_date_key;
ALTER TABLE daily_digests ADD CONSTRAINT daily_digests_date_topic_key UNIQUE (digest_date, topic);

-- 3. Add topic to collector cache
ALTER TABLE digest_collector_cache ADD COLUMN IF NOT EXISTS topic TEXT NOT NULL DEFAULT 'ai';
ALTER TABLE digest_collector_cache DROP CONSTRAINT IF EXISTS digest_collector_cache_digest_date_source_key;
ALTER TABLE digest_collector_cache ADD CONSTRAINT digest_collector_cache_date_source_topic_key UNIQUE (digest_date, source, topic);

-- 4. Update RPC to accept topic parameter
CREATE OR REPLACE FUNCTION claim_digest_generation(p_date DATE, p_topic TEXT DEFAULT 'ai')
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE v_id UUID; v_status TEXT;
BEGIN
    -- 1. Reclaim stale locks (crashed generators, 150s timeout)
    UPDATE daily_digests SET status = 'failed', updated_at = NOW()
    WHERE digest_date = p_date AND topic = p_topic
      AND status IN ('collecting', 'analyzing')
      AND updated_at < NOW() - INTERVAL '150 seconds';

    -- 2. Atomic claim: insert OR reclaim failed
    INSERT INTO daily_digests (digest_date, topic, status, updated_at)
    VALUES (p_date, p_topic, 'collecting', NOW())
    ON CONFLICT (digest_date, topic) DO UPDATE
      SET status = 'collecting', updated_at = NOW()
      WHERE daily_digests.status = 'failed'
    RETURNING id INTO v_id;

    -- 3. Did we win?
    IF v_id IS NOT NULL THEN
        RETURN jsonb_build_object('claimed', true, 'digest_id', v_id, 'current_status', 'collecting');
    ELSE
        SELECT d.id, d.status INTO v_id, v_status
        FROM daily_digests d WHERE d.digest_date = p_date AND d.topic = p_topic;
        RETURN jsonb_build_object('claimed', false, 'digest_id', v_id, 'current_status', v_status);
    END IF;
END;
$$;
