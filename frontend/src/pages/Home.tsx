import { useEffect, useRef } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Heading, Text, Stack, Link, Flex } from '@chakra-ui/react';
import { useAuth } from '../hooks/useAuth';

const SYMBOLS = '+-=*/<>{}[]|\\~^#@!?$%&;:.,0123456789';
const COLUMN_GAP = 22;
const FONT_SIZE = 14;

function MatrixCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let columns: number[] = [];

    function resize() {
      canvas!.width = window.innerWidth;
      canvas!.height = window.innerHeight;
      const colCount = Math.floor(canvas!.width / COLUMN_GAP);
      columns = Array.from({ length: colCount }, () =>
        Math.random() * canvas!.height
      );
    }

    resize();
    window.addEventListener('resize', resize);

    function draw() {
      ctx!.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx!.fillRect(0, 0, canvas!.width, canvas!.height);
      ctx!.font = `${FONT_SIZE}px monospace`;

      for (let i = 0; i < columns.length; i++) {
        const char = SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)];
        const x = i * COLUMN_GAP;
        const y = columns[i];

        // Gradient from bright to dim
        const brightness = Math.random();
        if (brightness > 0.95) {
          ctx!.fillStyle = '#ffffff';
        } else if (brightness > 0.7) {
          ctx!.fillStyle = '#4ade80';
        } else {
          ctx!.fillStyle = 'rgba(74, 222, 128, 0.4)';
        }

        ctx!.fillText(char, x, y);

        if (y > canvas!.height && Math.random() > 0.975) {
          columns[i] = 0;
        }
        columns[i] += FONT_SIZE + Math.random() * 4;
      }

      animId = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
      }}
    />
  );
}

function RippleOverlay() {
  return (
    <Box
      position="absolute"
      inset={0}
      zIndex={1}
      pointerEvents="none"
      background="radial-gradient(ellipse at 50% 50%, transparent 0%, rgba(0,0,0,0.3) 60%, rgba(0,0,0,0.7) 100%)"
    />
  );
}

export default function Home() {
  const { user } = useAuth();

  return (
    <Box position="relative" minH="100vh" bg="black" overflow="hidden">
      <MatrixCanvas />
      <RippleOverlay />

      {/* Content */}
      <Flex
        position="relative"
        zIndex={2}
        minH="100vh"
        direction="column"
        alignItems="center"
        justifyContent="center"
        px={4}
        textAlign="center"
      >
        <Stack gap={6} maxW="2xl" alignItems="center">
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

          <Text color="gray.300" fontSize="lg" maxW="lg">
            AI-powered trend analysis across Reddit, YouTube, and Amazon.
            Get structured insights with sentiment analysis and source breakdowns.
          </Text>

          <Stack direction="row" gap={4} pt={4}>
            {user ? (
              <>
                <Link asChild>
                  <RouterLink to="/analyze">
                    <Button colorPalette="green" size="lg">
                      Start Analyzing
                    </Button>
                  </RouterLink>
                </Link>
                <Link asChild>
                  <RouterLink to="/dashboard">
                    <Button variant="outline" size="lg" color="white" borderColor="gray.600">
                      Dashboard
                    </Button>
                  </RouterLink>
                </Link>
              </>
            ) : (
              <>
                <Link asChild>
                  <RouterLink to="/signup">
                    <Button colorPalette="green" size="lg">
                      Get Started
                    </Button>
                  </RouterLink>
                </Link>
                <Link asChild>
                  <RouterLink to="/login">
                    <Button variant="outline" size="lg" color="white" borderColor="gray.600">
                      Sign In
                    </Button>
                  </RouterLink>
                </Link>
              </>
            )}
          </Stack>
        </Stack>

        {/* Feature highlights */}
        <Flex
          mt={20}
          gap={8}
          flexWrap="wrap"
          justifyContent="center"
          maxW="4xl"
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
            <Box
              key={f.title}
              bg="rgba(255,255,255,0.05)"
              borderWidth="1px"
              borderColor="gray.800"
              borderRadius="lg"
              p={6}
              maxW="xs"
              backdropFilter="blur(8px)"
            >
              <Heading size="md" color="white" mb={2}>
                {f.title}
              </Heading>
              <Text color="gray.400" fontSize="sm">
                {f.desc}
              </Text>
            </Box>
          ))}
        </Flex>
      </Flex>
    </Box>
  );
}
