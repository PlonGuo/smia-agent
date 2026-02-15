import { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  Heading,
  Stack,
  Text,
  Badge,
  Code,
} from '@chakra-ui/react';
import { useAuth } from '../hooks/useAuth';
import { useColorMode } from '../hooks/useColorMode';
import { getBindCode } from '../lib/api';
import { supabase } from '../lib/supabase';
import { toaster } from '../lib/toaster';
import { Moon, Sun, LinkIcon, CheckCircle } from 'lucide-react';

interface BindingRow {
  telegram_user_id: number | null;
  bound_at: string | null;
}

export default function Settings() {
  const { user, signOut } = useAuth();
  const { colorMode, toggleColorMode } = useColorMode();
  const [bindCode, setBindCode] = useState<string | null>(null);
  const [bindExpires, setBindExpires] = useState<string | null>(null);
  const [bindLoading, setBindLoading] = useState(false);
  const [isBound, setIsBound] = useState(false);
  const [bindingLoading, setBindingLoading] = useState(true);

  // Fetch current binding status on mount
  useEffect(() => {
    if (!user) return;

    const fetchBinding = async () => {
      const { data } = await supabase
        .from('user_bindings')
        .select('telegram_user_id, bound_at')
        .eq('user_id', user.id)
        .maybeSingle();

      if (data?.telegram_user_id) {
        setIsBound(true);
        setBindCode(null); // Clear any displayed code
      }
      setBindingLoading(false);
    };

    fetchBinding();
  }, [user]);

  // Subscribe to Realtime changes on user_bindings
  useEffect(() => {
    if (!user) return;

    const channel = supabase
      .channel('binding-status')
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'user_bindings',
          filter: `user_id=eq.${user.id}`,
        },
        (payload) => {
          const row = payload.new as BindingRow;
          if (row.telegram_user_id) {
            setIsBound(true);
            setBindCode(null);
            toaster.success({ title: 'Telegram linked successfully!' });
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user]);

  const handleGenerateCode = async () => {
    setBindLoading(true);
    try {
      const data = await getBindCode();
      setBindCode(data.bind_code);
      setBindExpires(new Date(data.expires_at).toLocaleTimeString());
      toaster.success({ title: 'Bind code generated' });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate code';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setBindLoading(false);
    }
  };

  return (
    <Box>
      <Heading size="xl" mb={6}>
        Settings
      </Heading>

      <Stack gap={6} maxW="2xl">
        {/* Account info */}
        <Card.Root>
          <Card.Header>
            <Heading size="md">Account</Heading>
          </Card.Header>
          <Card.Body>
            <Stack gap={3}>
              <Box>
                <Text fontSize="sm" color="fg.muted">
                  Email
                </Text>
                <Text fontWeight="medium">{user?.email ?? '—'}</Text>
              </Box>
              <Box>
                <Text fontSize="sm" color="fg.muted">
                  Registered
                </Text>
                <Text fontWeight="medium">
                  {user?.created_at
                    ? new Date(user.created_at).toLocaleDateString()
                    : '—'}
                </Text>
              </Box>
            </Stack>
          </Card.Body>
        </Card.Root>

        {/* Theme */}
        <Card.Root>
          <Card.Header>
            <Heading size="md">Appearance</Heading>
          </Card.Header>
          <Card.Body>
            <Button variant="outline" onClick={toggleColorMode}>
              {colorMode === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
              {colorMode === 'dark' ? 'Light Mode' : 'Dark Mode'}
            </Button>
          </Card.Body>
        </Card.Root>

        {/* Telegram Binding */}
        <Card.Root>
          <Card.Header>
            <Heading size="md">Telegram Integration</Heading>
          </Card.Header>
          <Card.Body>
            <Stack gap={4}>
              {bindingLoading ? (
                <Text fontSize="sm" color="fg.muted">
                  Loading binding status...
                </Text>
              ) : isBound ? (
                <Box
                  p={4}
                  borderWidth="1px"
                  borderRadius="md"
                  borderColor="green.500"
                >
                  <Stack direction="row" align="center" gap={2}>
                    <CheckCircle size={20} color="var(--chakra-colors-green-500)" />
                    <Text fontWeight="medium" color="green.500">
                      Telegram Linked
                    </Text>
                  </Stack>
                  <Text fontSize="sm" color="fg.muted" mt={2}>
                    Your Telegram account is connected. Use <Code>/analyze topic</Code>{' '}
                    in the bot to run analyses from Telegram.
                  </Text>
                </Box>
              ) : (
                <>
                  <Text fontSize="sm" color="fg.muted">
                    Link your Telegram account to use the SmIA bot. Generate a code
                    below and send <Code>/bind CODE</Code> to the bot.
                  </Text>

                  {bindCode ? (
                    <Box
                      p={4}
                      borderWidth="1px"
                      borderRadius="md"
                      textAlign="center"
                    >
                      <Text fontSize="sm" color="fg.muted" mb={1}>
                        Your bind code
                      </Text>
                      <Text
                        fontSize="3xl"
                        fontWeight="bold"
                        fontFamily="mono"
                        letterSpacing="0.2em"
                      >
                        {bindCode}
                      </Text>
                      {bindExpires && (
                        <Badge mt={2} variant="subtle">
                          Expires at {bindExpires}
                        </Badge>
                      )}
                      <Text fontSize="xs" color="fg.muted" mt={2}>
                        Send <Code>/bind {bindCode}</Code> to @plonguo_bot on Telegram
                      </Text>
                    </Box>
                  ) : (
                    <Button
                      variant="outline"
                      onClick={handleGenerateCode}
                      loading={bindLoading}
                      loadingText="Generating..."
                    >
                      <LinkIcon size={16} />
                      Generate Bind Code
                    </Button>
                  )}
                </>
              )}
            </Stack>
          </Card.Body>
        </Card.Root>

        {/* Danger zone */}
        <Card.Root borderColor="red.500" borderWidth="1px">
          <Card.Header>
            <Heading size="md" color="red.500">
              Danger Zone
            </Heading>
          </Card.Header>
          <Card.Body>
            <Button colorPalette="red" variant="outline" onClick={signOut}>
              Sign Out
            </Button>
          </Card.Body>
        </Card.Root>
      </Stack>
    </Box>
  );
}
