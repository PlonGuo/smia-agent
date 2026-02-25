import { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Button,
  Flex,
  Heading,
  Skeleton,
  Stack,
  Text,
} from '@chakra-ui/react';
import { useDigestPermissions } from '../hooks/useDigestPermissions';
import { useRealtimeSubscription } from '../hooks/useRealtimeSubscription';
import { getAccessRequests, getAdmins } from '../lib/api';
import type { AccessRequest, Admin as AdminType } from '../lib/api';
import { toaster } from '../lib/toaster';
import RequestsTable from '../components/admin/RequestsTable';
import AdminsManager from '../components/admin/AdminsManager';
import { useAuth } from '../hooks/useAuth';
import { Shield, Users } from 'lucide-react';

type Tab = 'requests' | 'admins';

export default function Admin() {
  const { user } = useAuth();
  const { isAdmin, accessStatus } = useDigestPermissions();
  const [tab, setTab] = useState<Tab>('requests');
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [admins, setAdmins] = useState<AdminType[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [reqData, adminData] = await Promise.all([
        getAccessRequests(),
        getAdmins(),
      ]);
      setRequests(reqData.requests);
      setAdmins(adminData.admins);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load admin data';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAdmin) fetchData();
  }, [isAdmin, fetchData]);

  // Realtime: auto-refresh when new requests come in
  useRealtimeSubscription('digest_access_requests', 'INSERT', useCallback(() => {
    fetchData();
  }, [fetchData]));

  if (accessStatus === 'loading') {
    return (
      <Box>
        <Heading size="xl" mb={6}>Admin</Heading>
        <Stack gap={4}>
          {[1, 2, 3].map((i) => <Skeleton key={i} height="60px" />)}
        </Stack>
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box textAlign="center" py={16}>
        <Heading size="lg" mb={4}>Access Denied</Heading>
        <Text color="fg.muted">
          You need admin privileges to access this page.
        </Text>
      </Box>
    );
  }

  const pendingCount = requests.filter((r) => r.status === 'pending').length;

  return (
    <Box>
      <Heading size="xl" mb={6}>Admin Dashboard</Heading>

      {/* Tabs */}
      <Flex gap={2} mb={6}>
        <Button
          className="btn-silicone"
          variant={tab === 'requests' ? 'subtle' : 'ghost'}
          size="sm"
          onClick={() => setTab('requests')}
        >
          <Users size={16} />
          Access Requests
          {pendingCount > 0 && (
            <Box
              as="span"
              bg="red.500"
              color="white"
              borderRadius="full"
              px={2}
              py={0}
              fontSize="xs"
              ml={1}
            >
              {pendingCount}
            </Box>
          )}
        </Button>
        <Button
          className="btn-silicone"
          variant={tab === 'admins' ? 'subtle' : 'ghost'}
          size="sm"
          onClick={() => setTab('admins')}
        >
          <Shield size={16} />
          Admins ({admins.length})
        </Button>
      </Flex>

      {loading ? (
        <Stack gap={4}>
          {[1, 2, 3].map((i) => <Skeleton key={i} height="80px" />)}
        </Stack>
      ) : tab === 'requests' ? (
        <RequestsTable requests={requests} onUpdate={fetchData} />
      ) : (
        <AdminsManager
          admins={admins}
          currentUserId={user?.id || ''}
          onUpdate={fetchData}
        />
      )}
    </Box>
  );
}
