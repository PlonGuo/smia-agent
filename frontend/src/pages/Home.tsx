import { lazy, Suspense } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Heading, Text, Stack, Link, Flex } from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import FluidHalo from '../components/landing/FluidHalo';

const ParticleScene = lazy(() => import('../components/landing/ParticleScene'));

const MotionBox = motion.create(Box);
const MotionStack = motion.create(Stack);
const MotionFlex = motion.create(Flex);

const cardContainerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.15, delayChildren: 0.6 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' as const } },
};

export default function Home() {
  const { user } = useAuth();

  return (
    <Box position="relative" minH="100dvh" bg="black" overflow="hidden">
      <FluidHalo />
      <Suspense fallback={null}>
        <ParticleScene />
      </Suspense>

      {/* Content */}
      <Flex
        position="relative"
        zIndex={2}
        minH="100dvh"
        direction="column"
        alignItems="center"
        justifyContent="center"
        px={4}
        py={{ base: 16, md: 4 }}
        textAlign="center"
      >
        <MotionStack
          gap={6}
          maxW="2xl"
          alignItems="center"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          <Heading
            size="4xl"
            color="white"
            fontWeight="bold"
            lineHeight="1.1"
          >
            Social Media
            <br />
            <Text as="span" color="green.400">
              Intelligence Agent
            </Text>
          </Heading>

          <MotionBox
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <Text color="gray.300" fontSize="lg" maxW="lg">
              AI-powered trend analysis across Reddit, YouTube, and Amazon.
              Get structured insights with sentiment analysis and source breakdowns.
            </Text>
          </MotionBox>

          <MotionBox
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <Stack direction="row" gap={4} pt={4}>
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
          </MotionBox>
        </MotionStack>

        {/* Feature highlights */}
        <MotionFlex
          mt={{ base: 10, md: 20 }}
          gap={{ base: 4, md: 8 }}
          flexWrap="wrap"
          justifyContent="center"
          maxW="4xl"
          variants={cardContainerVariants}
          initial="hidden"
          animate="visible"
        >
          {[
            {
              title: 'Multi-Source Crawling',
              desc: 'Aggregates data from Reddit, YouTube, and Amazon in real-time.',
            },
            {
              title: 'AI Analysis',
              desc: 'Structured trend reports with sentiment scoring and key insights.',
            },
            {
              title: 'Cross-Platform',
              desc: 'Use via web dashboard or Telegram bot with synced history.',
            },
          ].map((f) => (
            <MotionBox
              key={f.title}
              variants={cardVariants}
              bg="rgba(0, 0, 0, 0.4)"
              borderWidth="1px"
              borderColor="rgba(74, 222, 128, 0.15)"
              borderRadius="xl"
              p={6}
              maxW="xs"
              backdropFilter="blur(16px)"
              boxShadow="0 8px 32px rgba(0, 0, 0, 0.3)"
              _hover={{
                borderColor: 'rgba(74, 222, 128, 0.3)',
                boxShadow: '0 8px 32px rgba(74, 222, 128, 0.1)',
              }}
              style={{ transition: 'border-color 0.3s ease, box-shadow 0.3s ease' }}
            >
              <Heading size="md" color="white" mb={2}>
                {f.title}
              </Heading>
              <Text color="gray.400" fontSize="sm">
                {f.desc}
              </Text>
            </MotionBox>
          ))}
        </MotionFlex>
      </Flex>
    </Box>
  );
}
