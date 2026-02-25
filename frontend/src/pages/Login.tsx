import { useState } from 'react';
import { useNavigate, useSearchParams, Link as RouterLink } from 'react-router-dom';
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

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { signIn, signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTo = searchParams.get('redirect') || '/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await signIn(email, password);
      navigate(redirectTo);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Sign in failed';
      console.error('Login failed:', message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    try {
      await signInWithGoogle();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'OAuth failed';
      console.error('Google sign-in failed:', message);
    }
  };

  return (
    <Box
      display="flex"
      alignItems={{ base: 'flex-start', md: 'center' }}
      justifyContent="center"
      flex={1}
      pt={{ base: 4, md: 0 }}
    >
      <Card.Root className="glass-panel" maxW="md" w="full">
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
                className="btn-silicone"
                type="submit"
                colorPalette="green"
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
            <Button className="btn-silicone" variant="outline" w="full" onClick={handleGoogle}>
              Continue with Google
            </Button>
          </Stack>
        </Card.Body>
        <Card.Footer justifyContent="center">
          <Text fontSize="sm" color="fg.muted">
            Don&apos;t have an account?{' '}
            <Link asChild colorPalette="green">
              <RouterLink to="/signup">Sign up</RouterLink>
            </Link>
          </Text>
        </Card.Footer>
      </Card.Root>
    </Box>
  );
}
