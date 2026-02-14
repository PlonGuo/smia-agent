import { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  Field,
  Heading,
  Input,
  Stack,
  Text,
  Link,
  Separator,
} from '@chakra-ui/react';
import { useAuth } from '../hooks/useAuth';
import { toaster } from '../lib/toaster';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { signIn, signInWithGoogle } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await signIn(email, password);
      navigate('/dashboard');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Sign in failed';
      toaster.error({ title: 'Login failed', description: message });
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    try {
      await signInWithGoogle();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'OAuth failed';
      toaster.error({ title: 'Google sign-in failed', description: message });
    }
  };

  return (
    <Box
      minH="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      bg={{ base: 'gray.50', _dark: 'gray.950' }}
      px={4}
    >
      <Card.Root maxW="md" w="full">
        <Card.Header textAlign="center">
          <Heading size="xl" mb={1}>
            Welcome back
          </Heading>
          <Text color="fg.muted">Sign in to your SmIA account</Text>
        </Card.Header>
        <Card.Body>
          <form onSubmit={handleSubmit}>
            <Stack gap={4}>
              <Field.Root>
                <Field.Label>Email</Field.Label>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </Field.Root>
              <Field.Root>
                <Field.Label>Password</Field.Label>
                <Input
                  type="password"
                  placeholder="Your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </Field.Root>
              <Button
                type="submit"
                colorPalette="blue"
                w="full"
                loading={loading}
                loadingText="Signing in..."
              >
                Sign In
              </Button>
            </Stack>
          </form>
          <Stack gap={4} mt={4}>
            <Separator />
            <Button variant="outline" w="full" onClick={handleGoogle}>
              Continue with Google
            </Button>
          </Stack>
        </Card.Body>
        <Card.Footer justifyContent="center">
          <Text fontSize="sm" color="fg.muted">
            Don&apos;t have an account?{' '}
            <Link asChild colorPalette="blue">
              <RouterLink to="/signup">Sign up</RouterLink>
            </Link>
          </Text>
        </Card.Footer>
      </Card.Root>
    </Box>
  );
}
