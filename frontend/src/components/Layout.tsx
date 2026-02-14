import { Link as RouterLink, useLocation } from 'react-router-dom';
import {
  Box,
  Flex,
  HStack,
  Button,
  Heading,
  Link,
  Spacer,
  IconButton,
} from '@chakra-ui/react';
import { useAuth } from '../hooks/useAuth';
import { useColorMode } from '../hooks/useColorMode';
import { Search, LayoutDashboard, Settings, LogOut, Moon, Sun } from 'lucide-react';

const NAV_ITEMS = [
  { label: 'Analyze', path: '/analyze', icon: Search },
  { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Settings', path: '/settings', icon: Settings },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { signOut, user } = useAuth();
  const location = useLocation();
  const { colorMode, toggleColorMode } = useColorMode();

  return (
    <Box minH="100vh" bg={{ base: 'gray.50', _dark: 'gray.950' }}>
      <Flex
        as="nav"
        px={6}
        py={3}
        borderBottomWidth="1px"
        borderColor={{ base: 'gray.200', _dark: 'gray.800' }}
        bg={{ base: 'white', _dark: 'gray.900' }}
        alignItems="center"
      >
        <Link asChild>
          <RouterLink to="/">
            <Heading size="md" fontWeight="bold">
              SmIA
            </Heading>
          </RouterLink>
        </Link>

        {user && (
          <HStack gap={1} ml={8}>
            {NAV_ITEMS.map(({ label, path, icon: Icon }) => (
              <Link asChild key={path}>
                <RouterLink to={path}>
                  <Button
                    variant={location.pathname === path ? 'subtle' : 'ghost'}
                    size="sm"
                  >
                    <Icon size={16} />
                    {label}
                  </Button>
                </RouterLink>
              </Link>
            ))}
          </HStack>
        )}

        <Spacer />

        <HStack gap={2}>
          <IconButton
            aria-label="Toggle color mode"
            variant="ghost"
            size="sm"
            onClick={toggleColorMode}
          >
            {colorMode === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </IconButton>
          {user ? (
            <Button variant="ghost" size="sm" onClick={signOut}>
              <LogOut size={16} />
              Logout
            </Button>
          ) : (
            <HStack gap={1}>
              <Link asChild>
                <RouterLink to="/login">
                  <Button
                    variant={location.pathname === '/login' ? 'subtle' : 'ghost'}
                    size="sm"
                  >
                    Sign In
                  </Button>
                </RouterLink>
              </Link>
              <Link asChild>
                <RouterLink to="/signup">
                  <Button
                    variant={location.pathname === '/signup' ? 'solid' : 'outline'}
                    colorPalette="green"
                    size="sm"
                  >
                    Sign Up
                  </Button>
                </RouterLink>
              </Link>
            </HStack>
          )}
        </HStack>
      </Flex>
      <Box as="main" maxW="7xl" mx="auto" px={6} py={8}>
        {children}
      </Box>
    </Box>
  );
}
