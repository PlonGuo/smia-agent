import { useEffect, useState, useCallback } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Flex,
  Heading,
  Link,
  Text,
} from '@chakra-ui/react';
import { useRealtimeSubscription } from '../hooks/useRealtimeSubscription';
import { getTodayDigest } from '../lib/api';
import type { DailyDigest } from '../lib/api';
import { toaster } from '../lib/toaster';
import DigestHeader from '../components/digest/DigestHeader';
import DigestSkeleton from '../components/digest/DigestSkeleton';
import KanbanBoard from '../components/digest/KanbanBoard';
import ShareButton from '../components/digest/ShareButton';
import ExportButton from '../components/digest/ExportButton';
import { History } from 'lucide-react';

export default function AiDailyReport() {
  const [digest, setDigest] = useState<DailyDigest | null>(null);
  const [digestStatus, setDigestStatus] = useState<string>('loading');
  const [digestId, setDigestId] = useState<string | null>(null);

  // Fetch today's digest
  useEffect(() => {
    const fetchDigest = async () => {
      try {
        const result = await getTodayDigest();
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
  }, []);

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

  // State: digest is loading/generating
  if (digestStatus !== 'completed' || !digest) {
    return (
      <Box>
        <Heading size="xl" mb={6}>AI Daily Report</Heading>
        <DigestSkeleton status={digestStatus} />
      </Box>
    );
  }

  // State: completed digest
  return (
    <Box>
      <Flex justifyContent="space-between" alignItems="center" mb={6} flexWrap="wrap" gap={2}>
        <Heading size="xl">AI Daily Report</Heading>
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
