# Landing Page 3D Background Upgrade — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 2D Matrix canvas animation with a 3D interactive particle sphere, fluid green-dark halo background, and glassmorphism UI treatment on the landing page.

**Architecture:** New components (FluidHalo, ParticleSphere, ParticleScene) replace the MatrixCanvas/RippleOverlay in Home.tsx. Three.js is lazy-loaded so the bundle only impacts the landing page. Existing content, auth flow, and routing are unchanged.

**Tech Stack:** @react-three/fiber, @react-three/drei, @react-three/postprocessing, three, simplex-noise, framer-motion (already installed)

---

### Task 1: Install Three.js Dependencies

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install packages**

Run from `frontend/` directory:
```bash
cd /Users/plonguo/Git/smia-agent/frontend && pnpm add three @react-three/fiber @react-three/drei @react-three/postprocessing simplex-noise
```

**Step 2: Install Three.js type definitions**

```bash
cd /Users/plonguo/Git/smia-agent/frontend && pnpm add -D @types/three
```

**Step 3: Verify installation**

```bash
cd /Users/plonguo/Git/smia-agent/frontend && pnpm ls three @react-three/fiber @react-three/drei @react-three/postprocessing simplex-noise
```

Expected: All 5 packages listed with versions.

---

### Task 2: Create the FluidHalo Component

**Files:**
- Create: `frontend/src/components/landing/FluidHalo.tsx`

This is the CSS animated gradient background layer — overlapping soft radial gradients that blend green into dark with heavy blur, creating an organic fluid glow.

**Step 1: Create the component**

Create `frontend/src/components/landing/FluidHalo.tsx`:

```tsx
import { Box } from '@chakra-ui/react';

const keyframes = `
@keyframes halo-drift-1 {
  0%, 100% { transform: translate(0%, 0%) scale(1); opacity: 0.6; }
  33% { transform: translate(5%, -8%) scale(1.1); opacity: 0.8; }
  66% { transform: translate(-3%, 5%) scale(0.95); opacity: 0.5; }
}
@keyframes halo-drift-2 {
  0%, 100% { transform: translate(0%, 0%) scale(1); opacity: 0.4; }
  50% { transform: translate(-8%, 6%) scale(1.15); opacity: 0.7; }
}
@keyframes halo-drift-3 {
  0%, 100% { transform: translate(0%, 0%) scale(1.05); opacity: 0.3; }
  40% { transform: translate(6%, -4%) scale(0.9); opacity: 0.5; }
  80% { transform: translate(-4%, 8%) scale(1.1); opacity: 0.4; }
}
`;

export default function FluidHalo() {
  return (
    <>
      <style>{keyframes}</style>
      <Box position="absolute" inset={0} zIndex={0} overflow="hidden">
        {/* Primary green glow — center */}
        <Box
          position="absolute"
          top="50%"
          left="50%"
          width="120%"
          height="120%"
          marginTop="-60%"
          marginLeft="-60%"
          borderRadius="50%"
          background="radial-gradient(ellipse at center, rgba(74, 222, 128, 0.15) 0%, rgba(34, 197, 94, 0.08) 30%, rgba(5, 46, 22, 0.04) 60%, transparent 80%)"
          filter="blur(80px)"
          style={{ animation: 'halo-drift-1 12s ease-in-out infinite' }}
        />
        {/* Secondary green glow — offset top-right */}
        <Box
          position="absolute"
          top="30%"
          left="55%"
          width="80%"
          height="80%"
          marginTop="-40%"
          marginLeft="-40%"
          borderRadius="50%"
          background="radial-gradient(ellipse at center, rgba(34, 197, 94, 0.12) 0%, rgba(22, 101, 52, 0.06) 40%, transparent 70%)"
          filter="blur(100px)"
          style={{ animation: 'halo-drift-2 16s ease-in-out infinite' }}
        />
        {/* Tertiary dim glow — offset bottom-left */}
        <Box
          position="absolute"
          top="60%"
          left="40%"
          width="90%"
          height="90%"
          marginTop="-45%"
          marginLeft="-45%"
          borderRadius="50%"
          background="radial-gradient(ellipse at center, rgba(74, 222, 128, 0.08) 0%, rgba(5, 46, 22, 0.05) 35%, transparent 65%)"
          filter="blur(90px)"
          style={{ animation: 'halo-drift-3 20s ease-in-out infinite' }}
        />
      </Box>
    </>
  );
}
```

**Step 2: Verify dev server compiles**

```bash
cd /Users/plonguo/Git/smia-agent/frontend && pnpm dev
```

Visit `http://localhost:5173` — no errors in console. (Component not yet rendered on page, just confirming it compiles.)

---

### Task 3: Create the ParticleSphere Component

**Files:**
- Create: `frontend/src/components/landing/ParticleSphere.tsx`

The 3D particle sphere with green gradient colors, slow rotation, simplex noise "breathing", and mouse-follow tilt.

**Step 1: Create the component**

Create `frontend/src/components/landing/ParticleSphere.tsx`:

```tsx
import { useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';
import { createNoise3D } from 'simplex-noise';

const PARTICLE_COUNT_DETAIL = 12; // icosahedron detail level
const NOISE_SPEED = 0.3;
const NOISE_AMPLITUDE = 0.08;
const ROTATION_SPEED = 0.15;

export default function ParticleSphere() {
  const pointsRef = useRef<THREE.Points>(null);
  const noise3D = useMemo(() => createNoise3D(), []);

  // Store original positions for noise displacement
  const { positions, colors, originalPositions } = useMemo(() => {
    const geo = new THREE.IcosahedronGeometry(1.5, PARTICLE_COUNT_DETAIL);
    const posArray = geo.attributes.position.array as Float32Array;
    const original = new Float32Array(posArray);

    // Color gradient: bright green at top, dark green at bottom
    const colArray = new Float32Array(posArray.length);
    const brightGreen = new THREE.Color('#4ade80');
    const darkGreen = new THREE.Color('#166534');

    for (let i = 0; i < posArray.length; i += 3) {
      const y = posArray[i + 1];
      // Normalize y from [-1.5, 1.5] to [0, 1]
      const t = (y / 1.5 + 1) / 2;
      const color = new THREE.Color().lerpColors(darkGreen, brightGreen, t);
      colArray[i] = color.r;
      colArray[i + 1] = color.g;
      colArray[i + 2] = color.b;
    }

    geo.dispose();
    return { positions: posArray, colors: colArray, originalPositions: original };
  }, []);

  const { pointer } = useThree();

  useFrame((state) => {
    if (!pointsRef.current) return;
    const time = state.clock.elapsedTime;

    // Slow rotation
    pointsRef.current.rotation.y += ROTATION_SPEED * 0.01;
    pointsRef.current.rotation.x += ROTATION_SPEED * 0.005;

    // Mouse-follow tilt
    pointsRef.current.rotation.x += (pointer.y * 0.3 - pointsRef.current.rotation.x) * 0.02;
    pointsRef.current.rotation.z += (pointer.x * 0.2 - pointsRef.current.rotation.z) * 0.02;

    // Simplex noise displacement ("breathing")
    const posAttr = pointsRef.current.geometry.attributes.position;
    const posArr = posAttr.array as Float32Array;

    for (let i = 0; i < posArr.length; i += 3) {
      const ox = originalPositions[i];
      const oy = originalPositions[i + 1];
      const oz = originalPositions[i + 2];

      const noiseVal = noise3D(
        ox * 2 + time * NOISE_SPEED,
        oy * 2 + time * NOISE_SPEED,
        oz * 2 + time * NOISE_SPEED
      );

      const direction = new THREE.Vector3(ox, oy, oz).normalize();
      posArr[i] = ox + direction.x * noiseVal * NOISE_AMPLITUDE;
      posArr[i + 1] = oy + direction.y * noiseVal * NOISE_AMPLITUDE;
      posArr[i + 2] = oz + direction.z * noiseVal * NOISE_AMPLITUDE;
    }

    posAttr.needsUpdate = true;
  });

  return (
    <Points ref={pointsRef} positions={positions} colors={colors}>
      <PointMaterial
        vertexColors
        size={0.015}
        sizeAttenuation
        transparent
        opacity={0.9}
        depthWrite={false}
      />
    </Points>
  );
}
```

---

### Task 4: Create the ParticleScene Wrapper

**Files:**
- Create: `frontend/src/components/landing/ParticleScene.tsx`

Wraps the Canvas, camera, and Bloom post-processing. This is the component that gets lazy-loaded.

**Step 1: Create the component**

Create `frontend/src/components/landing/ParticleScene.tsx`:

```tsx
import { Canvas } from '@react-three/fiber';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import ParticleSphere from './ParticleSphere';

export default function ParticleScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 4], fov: 50 }}
      gl={{ alpha: true, antialias: true }}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 1,
      }}
    >
      <ambientLight intensity={0.5} />
      <ParticleSphere />
      <EffectComposer>
        <Bloom
          intensity={1.5}
          luminanceThreshold={0.2}
          luminanceSmoothing={0.9}
          mipmapBlur
        />
      </EffectComposer>
    </Canvas>
  );
}
```

---

### Task 5: Update Home.tsx — Replace Background and Add Glassmorphism + Framer Motion

**Files:**
- Modify: `frontend/src/pages/Home.tsx`

Replace MatrixCanvas + RippleOverlay with FluidHalo + ParticleScene (lazy-loaded). Add Framer Motion entry animations to the hero content. Enhance feature cards with glassmorphism.

**Step 1: Rewrite Home.tsx**

Replace the entire contents of `frontend/src/pages/Home.tsx` with:

```tsx
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

export default function Home() {
  const { user } = useAuth();

  return (
    <Box position="relative" minH="100vh" bg="black" overflow="hidden">
      {/* Layer 1: Fluid green-dark halo */}
      <FluidHalo />

      {/* Layer 2: 3D Particle sphere (lazy-loaded) */}
      <Suspense fallback={null}>
        <ParticleScene />
      </Suspense>

      {/* Layer 3: Content overlay */}
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
            transition={{ duration: 0.8, delay: 0.2, ease: 'easeOut' }}
          >
            <Text color="gray.300" fontSize="lg" maxW="lg">
              AI-powered trend analysis across Reddit, YouTube, and Amazon.
              Get structured insights with sentiment analysis and source breakdowns.
            </Text>
          </MotionBox>

          <MotionBox
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: 'easeOut' }}
          >
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
          </MotionBox>
        </MotionStack>

        {/* Feature highlights with glassmorphism */}
        <MotionFlex
          mt={20}
          gap={8}
          flexWrap="wrap"
          justifyContent="center"
          maxW="4xl"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6, ease: 'easeOut' }}
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
              transition="all 0.3s ease"
            >
              <Heading size="md" color="white" mb={2}>
                {f.title}
              </Heading>
              <Text color="gray.400" fontSize="sm">
                {f.desc}
              </Text>
            </Box>
          ))}
        </MotionFlex>
      </Flex>
    </Box>
  );
}
```

---

### Task 6: Visual Verification

**Step 1: Start dev server and verify**

```bash
cd /Users/plonguo/Git/smia-agent/frontend && pnpm dev
```

**Step 2: Take screenshot with Playwright MCP**

Navigate to `http://localhost:5173` and verify:
- [ ] Fluid green-dark halo animates smoothly in background
- [ ] 3D particle sphere renders with green gradient colors
- [ ] Sphere rotates slowly and "breathes" with noise displacement
- [ ] Moving mouse causes sphere to tilt toward cursor
- [ ] Bloom glow effect visible on particles
- [ ] Hero text fades in with staggered animation
- [ ] Feature cards have glassmorphism (frosted dark glass, green-tinted border)
- [ ] CTA buttons still work (Get Started → /signup, Sign In → /login)
- [ ] No console errors

**Step 3: Check build succeeds**

```bash
cd /Users/plonguo/Git/smia-agent/frontend && pnpm build
```

Expected: Build succeeds with no TypeScript or bundle errors.

---

### Task 7: Performance & Polish

**Step 1: Check lazy loading works**

Open browser DevTools → Network tab → reload page. Verify Three.js chunks only load on the landing page, not on `/login` or `/dashboard`.

**Step 2: Test responsive layout**

Use Playwright to check at mobile viewport (375px width) — sphere and UI should still look reasonable.

**Step 3: Fix any visual issues found during verification**

Adjust particle count, bloom intensity, halo opacity, animation speeds, glassmorphism values as needed based on visual review.

---
