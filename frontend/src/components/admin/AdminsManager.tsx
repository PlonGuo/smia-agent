import { useState } from 'react';
import {
  Box,
  Button,
  Card,
  Flex,
  Input,
  Stack,
  Text,
} from '@chakra-ui/react';
import { addAdmin, removeAdmin } from '../../lib/api';
import { toaster } from '../../lib/toaster';
import { Plus, Trash2, Shield } from 'lucide-react';

interface Admin {
  id: string;
  email: string;
  created_at: string;
}

interface Props {
  admins: Admin[];
  currentUserId: string;
  onUpdate: () => void;
}

export default function AdminsManager({ admins, onUpdate }: Props) {
  const [newEmail, setNewEmail] = useState('');
  const [addLoading, setAddLoading] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail.trim()) return;
    setAddLoading(true);
    try {
      await addAdmin(newEmail.trim());
      toaster.success({ title: `${newEmail} added as admin` });
      setNewEmail('');
      onUpdate();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add admin';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setAddLoading(false);
    }
  };

  const handleRemove = async (id: string) => {
    setRemovingId(id);
    try {
      await removeAdmin(id);
      toaster.success({ title: 'Admin removed' });
      onUpdate();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to remove admin';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <Stack gap={4}>
      <form onSubmit={handleAdd}>
        <Flex gap={2}>
          <Input
            placeholder="admin@example.com"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            size="sm"
            flex={1}
          />
          <Button
            className="btn-silicone"
            type="submit"
            size="sm"
            colorPalette="blue"
            variant="outline"
            loading={addLoading}
          >
            <Plus size={14} />
            Add Admin
          </Button>
        </Flex>
      </form>

      <Stack gap={2}>
        {admins.map((admin) => (
          <Card.Root className="glass-panel" key={admin.id} p={3}>
            <Flex alignItems="center" justifyContent="space-between">
              <Flex alignItems="center" gap={2}>
                <Shield size={16} />
                <Box>
                  <Text fontWeight="medium" fontSize="sm">
                    {admin.email}
                  </Text>
                  <Text fontSize="xs" color="fg.muted">
                    Since {new Date(admin.created_at).toLocaleDateString()}
                  </Text>
                </Box>
              </Flex>
              <Button
                className="btn-silicone"
                size="xs"
                colorPalette="red"
                variant="ghost"
                onClick={() => handleRemove(admin.id)}
                loading={removingId === admin.id}
              >
                <Trash2 size={14} />
              </Button>
            </Flex>
          </Card.Root>
        ))}
      </Stack>
    </Stack>
  );
}
