import { useEffect, useState, useCallback } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import {
  Box,
  Button,
  Flex,
  Heading,
  Link,
  Text,
} from '@chakra-ui/react';
import { useRealtimeSubscription } from '../hooks/useRealtimeSubscription';
import { getTodayDigest, getDigestTopics } from '../lib/api';
import type { DailyDigest } from '../lib/api';
import { toaster } from '../lib/toaster';
import DigestHeader from '../components/digest/DigestHeader';
import DigestSkeleton from '../components/digest/DigestSkeleton';
import KanbanBoard from '../components/digest/KanbanBoard';
import ShareButton from '../components/digest/ShareButton';
import ExportButton from '../components/digest/ExportButton';
import { History } from 'lucide-react';

interface TopicInfo {
  key: string;
  display_name: string;
}

export default function AiDailyReport() {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTopic = searchParams.get('topic') || 'ai';

  const [topics, setTopics] = useState<TopicInfo[]>([]);
  const [digest, setDigest] = useState<DailyDigest | null>(null);
  const [digestStatus, setDigestStatus] = useState<string>('loading');
  const [digestId, setDigestId] = useState<string | null>(null);

  // Load available topics
  useEffect(() => {
    getDigestTopics()
      .then((data) => setTopics(data.topics))
      .catch(() => setTopics([{ key: 'ai', display_name: 'AI Intelligence' }]));
  }, []);

  // Fetch today's digest for selected topic
  useEffect(() => {
    setDigest(null);
    setDigestId(null);
    setDigestStatus('loading');

    const fetchDigest = async () => {
      try {
        const result = await getTodayDigest(currentTopic);
        setDigestStatus(result.status);
        setDigestId(result.digest_id);
        if (result.digest) {
          setDigest(result.digest);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load digest';
        toaster.error({ title: 'Error', description: msg });
        setDigestStatus('error');
      }
    };

    fetchDigest();
  }, [currentTopic]);

  // Realtime: subscribe to digest status changes
  useRealtimeSubscription(
    'daily_digests',
    'UPDATE',
    useCallback((payload: { new: Record<string, unknown> }) => {
      const newRow = payload.new;
      if (newRow && digestId && newRow.id === digestId) {
        setDigestStatus(newRow.status as string);
        if (newRow.status === 'completed') {
          setDigest(newRow as unknown as DailyDigest);
        }
      }
    }, [digestId]),
    digestId ? `id=eq.${digestId}` : undefined,
  );

  const handleTopicChange = (topic: string) => {
    setSearchParams({ topic });
  };

  const topicDisplayName = topics.find((t) => t.key === currentTopic)?.display_name || 'Daily Report';

  // Topic tabs
  const topicTabs = topics.length > 1 && (
    <Flex gap={2} mb={4} overflowX="auto" pb={1} css={{ '&::-webkit-scrollbar': { display: 'none' } }}>
      {topics.map((t) => (
        <Button
          className="btn-silicone"
          key={t.key}
          size="sm"
          variant={currentTopic === t.key ? 'subtle' : 'ghost'}
          onClick={() => handleTopicChange(t.key)}
          flexShrink={0}
        >
          {t.display_name}
        </Button>
      ))}
    </Flex>
  );

  // State: digest is loading/generating
  if (digestStatus !== 'completed' || !digest) {
    return (
      <Box>
        <Heading size="xl" mb={6}>{topicDisplayName}</Heading>
        {topicTabs}
        <DigestSkeleton status={digestStatus} />
      </Box>
    );
  }

  // State: completed digest
  return (
    <Box>
      <Flex justifyContent="space-between" alignItems="center" mb={4} flexWrap="wrap" gap={2}>
        <Heading size="xl">{topicDisplayName}</Heading>
        <Flex gap={2}>
          <ShareButton digestId={digest.id} />
          <ExportButton digest={digest} />
          <Link asChild>
            <RouterLink to="/ai-daily-report/history">
              <Button className="btn-silicone" variant="ghost" size="sm">
                <History size={14} />
                History
              </Button>
            </RouterLink>
          </Link>
        </Flex>
      </Flex>
      {topicTabs}
      <DigestHeader digest={digest} />
      {digest.top_highlights && digest.top_highlights.length > 0 && (
        <Box className="glass-panel" p={4} mb={6}>
          <Heading size="sm" mb={3}>Top Highlights</Heading>
          {digest.top_highlights.map((h: string, i: number) => (
            <Text key={i} fontSize="sm" color="fg.muted" mb={1}>
              {i + 1}. {h}
            </Text>
          ))}
        </Box>
      )}
      <KanbanBoard items={digest.items || []} />
    </Box>
  );
}
