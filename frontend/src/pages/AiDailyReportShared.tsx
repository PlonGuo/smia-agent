import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Heading,
  Text,
} from '@chakra-ui/react';
import { getSharedDigest } from '../lib/api';
import type { DailyDigest } from '../lib/api';
import DigestHeader from '../components/digest/DigestHeader';
import DigestSkeleton from '../components/digest/DigestSkeleton';
import KanbanBoard from '../components/digest/KanbanBoard';

export default function AiDailyReportShared() {
  const { token } = useParams<{ token: string }>();
  const [digest, setDigest] = useState<DailyDigest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;

    const fetchShared = async () => {
      try {
        const data = await getSharedDigest(token);
        setDigest(data.digest);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load shared digest');
      } finally {
        setLoading(false);
      }
    };

    fetchShared();
  }, [token]);

  if (loading) {
    return <DigestSkeleton />;
  }

  if (error) {
    return (
      <Box textAlign="center" py={16}>
        <Heading size="lg" mb={4}>Share Link Error</Heading>
        <Text color="fg.muted">{error}</Text>
      </Box>
    );
  }

  if (!digest) {
    return (
      <Box textAlign="center" py={16}>
        <Heading size="lg" mb={4}>Not Found</Heading>
        <Text color="fg.muted">This shared link is invalid or has expired.</Text>
      </Box>
    );
  }

  return (
    <Box>
      <Heading size="xl" mb={2}>AI Daily Report (Shared)</Heading>
      <Text color="fg.muted" mb={6} fontSize="sm">
        This is a shared view. Sign up to get daily access.
      </Text>
      <DigestHeader digest={digest} />
      <KanbanBoard items={digest.items || []} />
    </Box>
  );
}
