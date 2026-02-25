import { useEffect, useState } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Heading,
  Link,
  Text,
} from '@chakra-ui/react';
import { useDigestPermissions } from '../hooks/useDigestPermissions';
import { getDigest } from '../lib/api';
import type { DailyDigest } from '../lib/api';
import DigestHeader from '../components/digest/DigestHeader';
import DigestSkeleton from '../components/digest/DigestSkeleton';
import KanbanBoard from '../components/digest/KanbanBoard';
import ShareButton from '../components/digest/ShareButton';
import ExportButton from '../components/digest/ExportButton';
import { ArrowLeft } from 'lucide-react';

export default function AiDailyReportDetail() {
  const { id } = useParams<{ id: string }>();
  const { hasAccess, accessStatus } = useDigestPermissions();
  const [digest, setDigest] = useState<DailyDigest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id || !hasAccess) return;

    const fetchDigest = async () => {
      try {
        const data = await getDigest(id);
        setDigest(data.digest);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load digest');
      } finally {
        setLoading(false);
      }
    };

    fetchDigest();
  }, [id, hasAccess]);

  if (accessStatus === 'loading' || loading) {
    return <DigestSkeleton />;
  }

  if (!hasAccess) {
    return (
      <Box textAlign="center" py={16}>
        <Heading size="lg" mb={4}>Access Required</Heading>
        <Text color="fg.muted">You need digest access to view this page.</Text>
      </Box>
    );
  }

  if (error || !digest) {
    return (
      <Box textAlign="center" py={16}>
        <Heading size="lg" mb={4}>Not Found</Heading>
        <Text color="fg.muted">{error || 'Digest not found.'}</Text>
      </Box>
    );
  }

  return (
    <Box>
      <Link asChild>
        <RouterLink to="/ai-daily-report/history">
          <Button className="btn-silicone" variant="ghost" size="sm" mb={4}>
            <ArrowLeft size={16} />
            Back to History
          </Button>
        </RouterLink>
      </Link>

      <DigestHeader digest={digest} />

      <Box mb={4} display="flex" gap={2}>
        <ShareButton digestId={digest.id} />
        <ExportButton digest={digest} />
      </Box>

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
