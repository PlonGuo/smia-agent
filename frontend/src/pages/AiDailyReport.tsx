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
import { useDigestPermissions } from '../hooks/useDigestPermissions';
import { useRealtimeSubscription } from '../hooks/useRealtimeSubscription';
import { getTodayDigest } from '../lib/api';
import { toaster } from '../lib/toaster';
import AccessRequestModal from '../components/digest/AccessRequestModal';
import DigestHeader from '../components/digest/DigestHeader';
import DigestSkeleton from '../components/digest/DigestSkeleton';
import KanbanBoard from '../components/digest/KanbanBoard';
import ShareButton from '../components/digest/ShareButton';
import ExportButton from '../components/digest/ExportButton';
import { Clock, History, XCircle } from 'lucide-react';

export default function AiDailyReport() {
  const { accessStatus, hasAccess } = useDigestPermissions();
  const [digest, setDigest] = useState<any>(null);
  const [digestStatus, setDigestStatus] = useState<string>('loading');
  const [digestId, setDigestId] = useState<string | null>(null);

  // Fetch today's digest once permission is confirmed
  useEffect(() => {
    if (!hasAccess) return;

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
  }, [hasAccess]);

  // Realtime: subscribe to digest status changes
  useRealtimeSubscription(
    'daily_digests',
    'UPDATE',
    useCallback((payload: any) => {
      const newRow = payload.new;
      if (newRow && digestId && newRow.id === digestId) {
        setDigestStatus(newRow.status);
        if (newRow.status === 'completed') {
          setDigest(newRow);
        }
      }
    }, [digestId]),
    digestId ? `id=eq.${digestId}` : undefined,
  );

  // Realtime: subscribe to access request approval
  useRealtimeSubscription(
    'digest_access_requests',
    'UPDATE',
    useCallback((payload: any) => {
      if (payload.new?.status === 'approved') {
        window.location.reload();
      }
    }, []),
  );

  // State: loading permission
  if (accessStatus === 'loading') {
    return <DigestSkeleton />;
  }

  // State: no access — show request form
  if (accessStatus === 'none' || accessStatus === 'rejected') {
    return (
      <Box>
        <Heading size="xl" mb={6}>AI Daily Report</Heading>
        {accessStatus === 'rejected' && (
          <Box className="glass-panel" p={4} mb={4} textAlign="center">
            <XCircle size={20} style={{ display: 'inline' }} />
            <Text color="fg.muted" mt={2}>
              Your previous request was not approved. You can submit a new request.
            </Text>
          </Box>
        )}
        <AccessRequestModal onSubmitted={() => window.location.reload()} />
      </Box>
    );
  }

  // State: pending approval
  if (accessStatus === 'pending') {
    return (
      <Box textAlign="center" py={16}>
        <Clock size={48} style={{ margin: '0 auto 16px' }} />
        <Heading size="lg" mb={4}>Request Pending</Heading>
        <Text color="fg.muted" maxW="md" mx="auto">
          Your access request is being reviewed by an admin.
          You'll receive an email when it's approved.
        </Text>
      </Box>
    );
  }

  // State: has access but digest is loading/generating
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
