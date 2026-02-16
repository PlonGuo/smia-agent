import { useState } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import {
  Box,
  Flex,
  HStack,
  Stack,
  Button,
  Heading,
  Link,
  Spacer,
  IconButton,
} from '@chakra-ui/react';
import { useAuth } from '../hooks/useAuth';
import { useColorMode } from '../hooks/useColorMode';
import { Search, LayoutDashboard, Settings, LogOut, Moon, Sun, Menu, X } from 'lucide-react';

const NAV_ITEMS = [
  { label: 'Analyze', path: '/analyze', icon: Search },
  { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { label: 'Settings', path: '/settings', icon: Settings },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { signOut, user } = useAuth();
  const location = useLocation();
  const { colorMode, toggleColorMode } = useColorMode();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const closeDrawer = () => setDrawerOpen(false);

  return (
    <Box minH="100dvh" className="app-bg" display="flex" flexDirection="column">
      <Flex
        as="nav"
        px={{ base: 4, md: 6 }}
        py={3}
        className="glass-nav"
        alignItems="center"
        position="sticky"
        top={0}
        zIndex={10}
      >
        <Link asChild>
          <RouterLink to="/">
            <Heading size="md" fontWeight="bold">
              SmIA
            </Heading>
          </RouterLink>
        </Link>

        {/* Desktop nav items */}
        {user && (
          <HStack gap={1} ml={8} display={{ base: 'none', md: 'flex' }}>
            {NAV_ITEMS.map(({ label, path, icon: Icon }) => (
              <Link asChild key={path}>
                <RouterLink to={path}>
                  <Button
                    className="btn-silicone"
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

        {/* Desktop right-side actions */}
        <HStack gap={2} display={{ base: 'none', md: 'flex' }}>
          <IconButton
            className="btn-silicone"
            aria-label="Toggle color mode"
            variant="ghost"
            size="sm"
            onClick={toggleColorMode}
          >
            {colorMode === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </IconButton>
          {user ? (
            <Button className="btn-silicone" variant="ghost" size="sm" onClick={signOut}>
              <LogOut size={16} />
              Logout
            </Button>
          ) : (
            <HStack gap={1}>
              <Link asChild>
                <RouterLink to="/login">
                  <Button
                    className="btn-silicone"
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
                    className="btn-silicone"
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

        {/* Mobile: theme toggle + hamburger */}
        <HStack gap={1} display={{ base: 'flex', md: 'none' }}>
          <IconButton
            className="btn-silicone"
            aria-label="Toggle color mode"
            variant="ghost"
            size="sm"
            onClick={toggleColorMode}
          >
            {colorMode === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </IconButton>
          <IconButton
            className="btn-silicone"
            aria-label={drawerOpen ? 'Close menu' : 'Open menu'}
            variant="ghost"
            size="sm"
            onClick={() => setDrawerOpen((prev) => !prev)}
          >
            {drawerOpen ? <X size={20} /> : <Menu size={20} />}
          </IconButton>
        </HStack>
      </Flex>

      {/* Mobile drawer overlay */}
      {drawerOpen && (
        <Box
          position="fixed"
          inset={0}
          bg="blackAlpha.600"
          zIndex={8}
          onClick={() => setDrawerOpen(false)}
          display={{ base: 'block', md: 'none' }}
        />
      )}

      {/* Mobile drawer panel */}
      <Box
        className="glass-drawer"
        position="fixed"
        top={0}
        right={0}
        h="100dvh"
        w="280px"
        zIndex={9}
        transform={drawerOpen ? 'translateX(0)' : 'translateX(100%)'}
        transition="transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
        display={{ base: 'flex', md: 'none' }}
        flexDirection="column"
        pt="72px"
        px={4}
        pb={6}
        overflowY="auto"
      >
        {/* Nav links */}
        {user && (
          <Stack gap={1} mb={4}>
            {NAV_ITEMS.map(({ label, path, icon: Icon }) => (
              <Link asChild key={path} onClick={closeDrawer}>
                <RouterLink to={path}>
                  <Button
                    className="btn-silicone"
                    variant={location.pathname === path ? 'subtle' : 'ghost'}
                    size="md"
                    w="full"
                    justifyContent="flex-start"
                    gap={3}
                  >
                    <Icon size={18} />
                    {label}
                  </Button>
                </RouterLink>
              </Link>
            ))}
          </Stack>
        )}

        <Spacer />

        {/* Bottom actions */}
        <Stack gap={2}>
          {user ? (
            <Button
              className="btn-silicone"
              variant="ghost"
              size="md"
              w="full"
              justifyContent="flex-start"
              gap={3}
              onClick={() => { closeDrawer(); signOut(); }}
            >
              <LogOut size={18} />
              Logout
            </Button>
          ) : (
            <>
              <Link asChild onClick={closeDrawer}>
                <RouterLink to="/login">
                  <Button
                    className="btn-silicone"
                    variant="ghost"
                    size="md"
                    w="full"
                  >
                    Sign In
                  </Button>
                </RouterLink>
              </Link>
              <Link asChild onClick={closeDrawer}>
                <RouterLink to="/signup">
                  <Button
                    className="btn-silicone"
                    colorPalette="green"
                    size="md"
                    w="full"
                  >
                    Sign Up
                  </Button>
                </RouterLink>
              </Link>
            </>
          )}
        </Stack>
      </Box>

      <Box as="main" flex={1} display="flex" flexDirection="column" maxW="7xl" mx="auto" w="full" px={{ base: 4, md: 6 }} py={{ base: 4, md: 8 }}>
        {children}
      </Box>
    </Box>
  );
}
