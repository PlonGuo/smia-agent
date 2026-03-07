import { Link as RouterLink } from 'react-router-dom';
import { Button, Stack, Link } from '@chakra-ui/react';
import { useAuth } from '../../hooks/useAuth';

export default function CTAButtons() {
  const { user } = useAuth();

  return (
    <Stack direction="row" gap={4}>
      {user ? (
        <>
          <Link asChild _hover={{ textDecoration: 'none' }}>
            <RouterLink to="/analyze">
              <Button className="btn-silicone" colorPalette="green" size="lg">
                Start Analyzing
              </Button>
            </RouterLink>
          </Link>
          <Link asChild _hover={{ textDecoration: 'none' }}>
            <RouterLink to="/dashboard">
              <Button className="btn-crystal" size="lg">
                Dashboard
              </Button>
            </RouterLink>
          </Link>
        </>
      ) : (
        <>
          <Link asChild _hover={{ textDecoration: 'none' }}>
            <RouterLink to="/signup">
              <Button className="btn-silicone" colorPalette="green" size="lg">
                Get Started
              </Button>
            </RouterLink>
          </Link>
          <Link asChild _hover={{ textDecoration: 'none' }}>
            <RouterLink to="/login">
              <Button className="btn-crystal" size="lg">
                Sign In
              </Button>
            </RouterLink>
          </Link>
        </>
      )}
    </Stack>
  );
}
