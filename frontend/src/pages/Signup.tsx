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

export default function Signup() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const { signUp, signInWithGoogle } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      toaster.error({
        title: 'Passwords do not match',
        description: 'Please make sure your passwords match.',
      });
      return;
    }
    if (password.length < 6) {
      toaster.error({
        title: 'Password too short',
        description: 'Password must be at least 6 characters.',
      });
      return;
    }
    setLoading(true);
    try {
      const message = await signUp(email, password);
      if (message) {
        toaster.success({ title: 'Account created', description: message });
        navigate('/login');
      } else {
        navigate('/dashboard');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Sign up failed';
      toaster.error({ title: 'Signup failed', description: msg });
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
            Create an account
          </Heading>
          <Text color="fg.muted">
            Get started with SmIA intelligence
          </Text>
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
                  placeholder="At least 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </Field.Root>
              <Field.Root>
                <Field.Label>Confirm Password</Field.Label>
                <Input
                  type="password"
                  placeholder="Confirm your password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                />
              </Field.Root>
              <Button
                type="submit"
                colorPalette="blue"
                w="full"
                loading={loading}
                loadingText="Creating account..."
              >
                Sign Up
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
            Already have an account?{' '}
            <Link asChild colorPalette="blue">
              <RouterLink to="/login">Sign in</RouterLink>
            </Link>
          </Text>
        </Card.Footer>
      </Card.Root>
    </Box>
  );
}
