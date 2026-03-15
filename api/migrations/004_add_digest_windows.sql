-- Migration 004: Add twice-daily digest windows (morning/afternoon, PT-based)
-- Allows two digests per day per topic: morning (10 AM PT) and afternoon (5 PM PT)

-- 1. Add digest_window column to daily_digests (default 'morning' for existing data)
ALTER TABLE daily_digests ADD COLUMN IF NOT EXISTS digest_window TEXT NOT NULL DEFAULT 'morning';

-- 2. Drop old unique constraint on (digest_date, topic), add composite unique (date + topic + digest_window)
ALTER TABLE daily_digests DROP CONSTRAINT IF EXISTS daily_digests_date_topic_key;
ALTER TABLE daily_digests ADD CONSTRAINT daily_digests_date_topic_window_key UNIQUE (digest_date, topic, digest_window);

-- 3. Add digest_window to collector cache
ALTER TABLE digest_collector_cache ADD COLUMN IF NOT EXISTS digest_window TEXT NOT NULL DEFAULT 'morning';
ALTER TABLE digest_collector_cache DROP CONSTRAINT IF EXISTS digest_collector_cache_date_source_topic_key;
ALTER TABLE digest_collector_cache ADD CONSTRAINT digest_collector_cache_date_source_topic_window_key UNIQUE (digest_date, source, topic, digest_window);

-- 4. Update RPC to accept window parameter
CREATE OR REPLACE FUNCTION claim_digest_generation(p_date DATE, p_topic TEXT DEFAULT 'ai', p_window TEXT DEFAULT 'morning')
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE v_id UUID; v_status TEXT;
BEGIN
    -- 1. Reclaim stale locks (crashed generators, 150s timeout)
    UPDATE daily_digests SET status = 'failed', updated_at = NOW()
    WHERE digest_date = p_date AND topic = p_topic AND digest_window = p_window
      AND status IN ('collecting', 'analyzing')
      AND updated_at < NOW() - INTERVAL '150 seconds';

    -- 2. Atomic claim: insert OR reclaim failed
    INSERT INTO daily_digests (digest_date, topic, digest_window, status, updated_at)
    VALUES (p_date, p_topic, p_window, 'collecting', NOW())
    ON CONFLICT (digest_date, topic, digest_window) DO UPDATE
      SET status = 'collecting', updated_at = NOW()
      WHERE daily_digests.status = 'failed'
    RETURNING id INTO v_id;

    -- 3. Did we win?
    IF v_id IS NOT NULL THEN
        RETURN jsonb_build_object('claimed', true, 'digest_id', v_id, 'current_status', 'collecting');
    ELSE
        SELECT d.id, d.status INTO v_id, v_status
        FROM daily_digests d WHERE d.digest_date = p_date AND d.topic = p_topic AND d.digest_window = p_window;
        RETURN jsonb_build_object('claimed', false, 'digest_id', v_id, 'current_status', v_status);
    END IF;
END;
$$;
