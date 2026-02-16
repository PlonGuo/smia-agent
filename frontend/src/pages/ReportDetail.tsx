import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  Flex,
  Heading,
  IconButton,
  Skeleton,
  Stack,
  Text,
} from '@chakra-ui/react';
import type { TrendReport } from '../../../shared/types';
import { getReport, deleteReport } from '../lib/api';
import { toaster } from '../lib/toaster';
import ReportViewer from '../components/ReportViewer';
import { ArrowLeft, Trash2, Share2 } from 'lucide-react';

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<TrendReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getReport(id)
      .then((data) => { if (!cancelled) setReport(data); })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Report not found');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id]);

  const handleDelete = async () => {
    if (!id) return;
    try {
      await deleteReport(id);
      toaster.success({ title: 'Report deleted' });
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Delete failed';
      toaster.error({ title: 'Error', description: msg });
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    toaster.success({ title: 'Link copied to clipboard' });
  };

  if (loading) {
    return (
      <Stack gap={6}>
        <Skeleton height="32px" width="40%" />
        <Card.Root className="glass-panel" p={6}>
          <Skeleton height="20px" width="70%" mb={3} />
          <Skeleton height="14px" width="100%" mb={2} />
          <Skeleton height="14px" width="90%" mb={2} />
          <Skeleton height="14px" width="60%" />
        </Card.Root>
        <Card.Root className="glass-panel" p={6}>
          <Skeleton height="200px" width="100%" />
        </Card.Root>
      </Stack>
    );
  }

  if (error || !report) {
    return (
      <Box py={12} textAlign="center">
        <Heading size="lg" mb={2}>
          Report Not Found
        </Heading>
        <Text color="fg.muted" mb={4}>
          {error || 'This report does not exist or has been deleted.'}
        </Text>
        <Button className="btn-silicone" variant="outline" onClick={() => navigate('/dashboard')}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Flex justifyContent="space-between" alignItems="center" mb={6}>
        <Button className="btn-silicone"
          variant="ghost"
          size="sm"
          onClick={() => navigate('/dashboard')}
        >
          <ArrowLeft size={16} />
          Back
        </Button>
        <Flex gap={2}>
          <IconButton className="btn-silicone"
            aria-label="Share report"
            variant="outline"
            size="sm"
            onClick={handleShare}
          >
            <Share2 size={16} />
          </IconButton>
          <IconButton className="btn-silicone"
            aria-label="Delete report"
            variant="outline"
            size="sm"
            colorPalette="red"
            onClick={handleDelete}
          >
            <Trash2 size={16} />
          </IconButton>
        </Flex>
      </Flex>

      <ReportViewer report={report} />
    </Box>
  );
}
