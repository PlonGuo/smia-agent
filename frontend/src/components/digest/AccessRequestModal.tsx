import { useState } from 'react';
import {
  Box,
  Button,
  Heading,
  Stack,
  Text,
  Textarea,
} from '@chakra-ui/react';
import { useAuth } from '../../hooks/useAuth';
import { requestDigestAccess } from '../../lib/api';
import { toaster } from '../../lib/toaster';
import { Send } from 'lucide-react';

interface Props {
  onSubmitted: () => void;
}

export default function AccessRequestModal({ onSubmitted }: Props) {
  const { user } = useAuth();
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!user?.email) return;
    setLoading(true);
    try {
      await requestDigestAccess(user.email, reason);
      toaster.success({ title: 'Access request submitted' });
      onSubmitted();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit request';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box className="glass-panel" p={8} maxW="lg" mx="auto" textAlign="center">
      <Heading size="lg" mb={4}>
        AI Daily Intelligence Digest
      </Heading>
      <Text color="fg.muted" mb={6}>
        This feature provides a daily curated digest of AI ecosystem updates from
        arXiv, GitHub, RSS, and Bluesky. Request access to get started.
      </Text>

      <Stack gap={4} maxW="md" mx="auto">
        <Box textAlign="left">
          <Text fontSize="sm" fontWeight="medium" mb={1}>
            Email
          </Text>
          <Text fontSize="sm" color="fg.muted">
            {user?.email}
          </Text>
        </Box>

        <Box textAlign="left">
          <Text fontSize="sm" fontWeight="medium" mb={1}>
            Reason (optional)
          </Text>
          <Textarea
            placeholder="Why do you need access?"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={500}
            rows={3}
          />
        </Box>

        <Button
          className="btn-silicone"
          colorPalette="blue"
          onClick={handleSubmit}
          loading={loading}
          loadingText="Submitting..."
        >
          <Send size={16} />
          Request Access
        </Button>
      </Stack>
    </Box>
  );
}
