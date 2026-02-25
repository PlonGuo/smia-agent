import { useState } from 'react';
import {
  Badge,
  Box,
  Button,
  Card,
  Flex,
  Stack,
  Text,
} from '@chakra-ui/react';
import { approveRequest, rejectRequest } from '../../lib/api';
import { toaster } from '../../lib/toaster';
import { Check, X } from 'lucide-react';

interface AccessRequest {
  id: string;
  email: string;
  reason: string;
  status: string;
  created_at: string;
  reviewed_at?: string;
}

interface Props {
  requests: AccessRequest[];
  onUpdate: () => void;
}

export default function RequestsTable({ requests, onUpdate }: Props) {
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const handleApprove = async (id: string) => {
    setLoadingId(id);
    try {
      await approveRequest(id);
      toaster.success({ title: 'Request approved' });
      onUpdate();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to approve';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setLoadingId(null);
    }
  };

  const handleReject = async (id: string) => {
    setLoadingId(id);
    try {
      await rejectRequest(id);
      toaster.success({ title: 'Request rejected' });
      onUpdate();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reject';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setLoadingId(null);
    }
  };

  const statusColor = (s: string) => {
    if (s === 'approved') return 'green';
    if (s === 'rejected') return 'red';
    return 'yellow';
  };

  if (requests.length === 0) {
    return (
      <Text color="fg.muted" fontSize="sm" textAlign="center" py={8}>
        No access requests yet.
      </Text>
    );
  }

  return (
    <Stack gap={3}>
      {requests.map((req) => (
        <Card.Root className="glass-panel" key={req.id} p={4}>
          <Flex justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={3}>
            <Box flex={1} minW="200px">
              <Flex alignItems="center" gap={2} mb={1}>
                <Text fontWeight="medium">{req.email}</Text>
                <Badge colorPalette={statusColor(req.status)} size="sm">
                  {req.status}
                </Badge>
              </Flex>
              {req.reason && (
                <Text fontSize="sm" color="fg.muted" mb={1}>
                  {req.reason}
                </Text>
              )}
              <Text fontSize="xs" color="fg.muted">
                {new Date(req.created_at).toLocaleDateString()}
              </Text>
            </Box>

            {req.status === 'pending' && (
              <Flex gap={2}>
                <Button
                  className="btn-silicone"
                  size="sm"
                  colorPalette="green"
                  variant="outline"
                  onClick={() => handleApprove(req.id)}
                  loading={loadingId === req.id}
                >
                  <Check size={14} />
                  Approve
                </Button>
                <Button
                  className="btn-silicone"
                  size="sm"
                  colorPalette="red"
                  variant="outline"
                  onClick={() => handleReject(req.id)}
                  loading={loadingId === req.id}
                >
                  <X size={14} />
                  Reject
                </Button>
              </Flex>
            )}
          </Flex>
        </Card.Root>
      ))}
    </Stack>
  );
}
