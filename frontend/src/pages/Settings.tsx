import { useState } from 'react';
import {
  Box,
  Button,
  Card,
  Heading,
  Stack,
  Text,
  Badge,
  Separator,
  Code,
} from '@chakra-ui/react';
import { useAuth } from '../hooks/useAuth';
import { useColorMode } from '../hooks/useColorMode';
import { getBindCode, unbindTelegram } from '../lib/api';
import { toaster } from '../lib/toaster';
import { Moon, Sun, LinkIcon, Unlink } from 'lucide-react';

export default function Settings() {
  const { user, signOut } = useAuth();
  const { colorMode, toggleColorMode } = useColorMode();
  const [bindCode, setBindCode] = useState<string | null>(null);
  const [bindExpires, setBindExpires] = useState<string | null>(null);
  const [bindLoading, setBindLoading] = useState(false);

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

  const handleUnbind = async () => {
    try {
      await unbindTelegram();
      toaster.success({ title: 'Telegram unlinked' });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to unlink';
      toaster.error({ title: 'Error', description: msg });
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

              <Separator />

              <Button
                variant="ghost"
                colorPalette="red"
                size="sm"
                onClick={handleUnbind}
              >
                <Unlink size={16} />
                Unlink Telegram
              </Button>
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
