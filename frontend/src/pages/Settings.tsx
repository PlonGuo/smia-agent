import { useEffect, useState, useCallback } from 'react';
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
import { useRealtimeSubscription } from '../hooks/useRealtimeSubscription';
import { getBindCode } from '../lib/api';
import { supabase } from '../lib/supabase';
import { toaster } from '../lib/toaster';
import { Moon, Sun, LinkIcon, CheckCircle, Clock } from 'lucide-react';

export default function Settings() {
  const { user, signOut } = useAuth();
  const { colorMode, toggleColorMode } = useColorMode();
  const [bindCode, setBindCode] = useState<string | null>(null);
  const [bindExpires, setBindExpires] = useState<string | null>(null);
  const [bindLoading, setBindLoading] = useState(false);
  const [bindingStatus, setBindingStatus] = useState<
    'loading' | 'none' | 'pending' | 'linked'
  >('loading');

  // Fetch current binding status on mount
  useEffect(() => {
    if (!user) return;

    const fetchBinding = async () => {
      const { data } = await supabase
        .from('user_bindings')
        .select('telegram_user_id, bind_code, code_expires_at, bound_at')
        .eq('user_id', user.id)
        .maybeSingle();

      if (!data) {
        // No row — user has never generated a code
        setBindingStatus('none');
      } else if (data.telegram_user_id) {
        // Row with telegram_user_id — fully linked
        setBindingStatus('linked');
      } else {
        // Row exists but no telegram_user_id — code generated, waiting for /bind
        setBindingStatus('pending');
        if (data.bind_code) {
          setBindCode(data.bind_code);
          if (data.code_expires_at) {
            const expiry = new Date(data.code_expires_at);
            if (expiry > new Date()) {
              setBindExpires(expiry.toLocaleTimeString());
            } else {
              // Code expired, treat as no active code
              setBindCode(null);
            }
          }
        }
      }
    };

    fetchBinding();
  }, [user]);

  // Realtime subscription for binding completion (replaces polling)
  useRealtimeSubscription(
    'user_bindings',
    'UPDATE',
    useCallback((payload: { new: Record<string, unknown> }) => {
      if (payload.new?.telegram_user_id) {
        setBindingStatus('linked');
        setBindCode(null);
        toaster.success({ title: 'Telegram linked successfully!' });
      }
    }, []),
    user ? `user_id=eq.${user.id}` : undefined,
  );

  const handleGenerateCode = async () => {
    setBindLoading(true);
    try {
      const data = await getBindCode();
      setBindCode(data.bind_code);
      setBindExpires(new Date(data.expires_at).toLocaleTimeString());
      setBindingStatus('pending');
      toaster.success({ title: 'Bind code generated' });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate code';
      toaster.error({ title: 'Error', description: msg });
    } finally {
      setBindLoading(false);
    }
  };

  const renderBindingContent = () => {
    if (bindingStatus === 'loading') {
      return (
        <Text fontSize="sm" color="fg.muted">
          Loading binding status...
        </Text>
      );
    }

    if (bindingStatus === 'linked') {
      return (
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
      );
    }

    if (bindingStatus === 'pending' && bindCode) {
      return (
        <>
          <Box
            p={4}
            borderWidth="1px"
            borderRadius="md"
            borderColor="yellow.500"
          >
            <Stack direction="row" align="center" gap={2} mb={2}>
              <Clock size={18} color="var(--chakra-colors-yellow-500)" />
              <Text fontWeight="medium" color="yellow.500">
                Waiting for Telegram
              </Text>
            </Stack>
            <Box textAlign="center" mt={2}>
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
          </Box>
          <Button className="btn-silicone"
            variant="outline"
            size="sm"
            onClick={handleGenerateCode}
            loading={bindLoading}
            loadingText="Generating..."
          >
            Generate New Code
          </Button>
        </>
      );
    }

    // bindingStatus === 'none' or 'pending' without a valid code
    return (
      <>
        <Text fontSize="sm" color="fg.muted">
          Link your Telegram account to use the SmIA bot. Generate a code
          below and send <Code>/bind CODE</Code> to the bot.
        </Text>
        <Button className="btn-silicone"
          variant="outline"
          onClick={handleGenerateCode}
          loading={bindLoading}
          loadingText="Generating..."
        >
          <LinkIcon size={16} />
          Generate Bind Code
        </Button>
      </>
    );
  };

  return (
    <Box>
      <Heading size="xl" mb={6} maxW="2xl" mx="auto" w="full">
        Settings
      </Heading>

      <Stack gap={6} maxW="2xl" mx="auto" w="full">
        {/* Account info */}
        <Card.Root className="glass-panel">
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
        <Card.Root className="glass-panel">
          <Card.Header>
            <Heading size="md">Appearance</Heading>
          </Card.Header>
          <Card.Body>
            <Button className="btn-silicone" variant="outline" onClick={(e) => toggleColorMode(e)}>
              {colorMode === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
              {colorMode === 'dark' ? 'Light Mode' : 'Dark Mode'}
            </Button>
          </Card.Body>
        </Card.Root>

        {/* Telegram Binding */}
        <Card.Root className="glass-panel">
          <Card.Header>
            <Heading size="md">Telegram Integration</Heading>
          </Card.Header>
          <Card.Body>
            <Stack gap={4}>
              <Box
                p={3}
                borderRadius="md"
                bg={{ base: 'gray.50', _dark: 'gray.800' }}
              >
                <Text fontSize="sm" color="fg.muted">
                  Open Telegram on your phone, search for{' '}
                  <Code>@plonguo_bot</Code>, open the chat, and send{' '}
                  <Code>/start</Code> to begin.
                </Text>
              </Box>
              {renderBindingContent()}
            </Stack>
          </Card.Body>
        </Card.Root>

        {/* Danger zone */}
        <Card.Root className="glass-panel-danger">
          <Card.Header>
            <Heading size="md" color="red.500">
              Danger Zone
            </Heading>
          </Card.Header>
          <Card.Body>
            <Button className="btn-silicone" colorPalette="red" variant="outline" onClick={signOut}>
              Sign Out
            </Button>
          </Card.Body>
        </Card.Root>
      </Stack>
    </Box>
  );
}
