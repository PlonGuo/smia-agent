import { useState, useMemo } from 'react';
import { Box, Flex, Heading, Text } from '@chakra-ui/react';
import { useColorMode } from '../../hooks/useColorMode';

/* ─── Color Palette (distinct hues) ─── */
const SOURCE_PALETTE: Record<string, { base: string; light: string; dark: string }> = {
  reddit:  { base: '#FF6D00', light: '#FF9E40', dark: '#C45400' },   // Vivid orange
  youtube: { base: '#FF1744', light: '#FF616F', dark: '#C4001D' },   // Rose-red
  amazon:  { base: '#FFAB00', light: '#FFD740', dark: '#C67C00' },   // Amber
};
const FALLBACK = { base: '#78909C', light: '#A7C0CD', dark: '#4B636E' };

/* ─── 3-D Donut Geometry ─── */
const CX = 150;
const CY = 95;
const OUTER_R = 80;
const INNER_R = 42;
const TILT = 0.55;     // vertical squash  ≈  cos(57°)
const DEPTH = 20;      // extrusion height (px)

const ORX = OUTER_R;
const ORY = OUTER_R * TILT;
const IRX = INNER_R;
const IRY = INNER_R * TILT;

/* ─── Helpers ─── */
interface Pt { x: number; y: number }

/** Convert angle (0° = top, clockwise) to point on a tilted ellipse */
function pt(cx: number, cy: number, rx: number, ry: number, deg: number): Pt {
  const r = ((deg - 90) * Math.PI) / 180;
  return { x: cx + rx * Math.cos(r), y: cy + ry * Math.sin(r) };
}

/** Produce an SVG arc command */
function arc(rx: number, ry: number, large: number, sweep: number, end: Pt) {
  return `A ${rx} ${ry} 0 ${large} ${sweep} ${end.x} ${end.y}`;
}

/* ─── Slice ─── */
interface Slice {
  key: string;
  label: string;
  value: number;
  pct: number;
  start: number;
  end: number;
  palette: { base: string; light: string; dark: string };
}

/* ─── SVG Path Builders ─── */

/** Top face of a donut slice (elliptical ring segment) */
function topPath(s: Slice): string {
  const span = s.end - s.start;

  // Full-circle edge-case: split into two 180° arcs
  if (span >= 359.99) {
    const a = pt(CX, CY, ORX, ORY, s.start);
    const b = pt(CX, CY, ORX, ORY, s.start + 180);
    const c = pt(CX, CY, IRX, IRY, s.start);
    const d = pt(CX, CY, IRX, IRY, s.start + 180);
    return [
      `M ${a.x} ${a.y}`,
      arc(ORX, ORY, 0, 1, b),
      arc(ORX, ORY, 0, 1, a),
      `L ${c.x} ${c.y}`,
      arc(IRX, IRY, 0, 0, d),
      arc(IRX, IRY, 0, 0, c),
      'Z',
    ].join(' ');
  }

  const oS = pt(CX, CY, ORX, ORY, s.start);
  const oE = pt(CX, CY, ORX, ORY, s.end);
  const iS = pt(CX, CY, IRX, IRY, s.start);
  const iE = pt(CX, CY, IRX, IRY, s.end);
  const big = span > 180 ? 1 : 0;

  return [
    `M ${oS.x} ${oS.y}`,
    arc(ORX, ORY, big, 1, oE),
    `L ${iE.x} ${iE.y}`,
    arc(IRX, IRY, big, 0, iS),
    'Z',
  ].join(' ');
}

/** Outer wall (3-D side) — only for the front-facing band (90°–270°) */
function wallPath(s: Slice): string {
  const wStart = Math.max(s.start, 90);
  const wEnd = Math.min(s.end, 270);
  if (wStart >= wEnd) return '';

  const span = wEnd - wStart;
  const big = span > 180 ? 1 : 0;

  const tS = pt(CX, CY, ORX, ORY, wStart);
  const tE = pt(CX, CY, ORX, ORY, wEnd);
  const bS: Pt = { x: tS.x, y: tS.y + DEPTH };
  const bE: Pt = { x: tE.x, y: tE.y + DEPTH };

  return [
    `M ${tS.x} ${tS.y}`,
    arc(ORX, ORY, big, 1, tE),
    `L ${bE.x} ${bE.y}`,
    arc(ORX, ORY, big, 0, bS),
    'Z',
  ].join(' ');
}

/* ─── Component ─── */
interface SourceDistributionProps {
  data: Record<string, number>;
}

export default function SourceDistribution({ data }: SourceDistributionProps) {
  const { colorMode } = useColorMode();
  const isDark = colorMode === 'dark';
  const [hovered, setHovered] = useState<string | null>(null);

  const slices = useMemo<Slice[]>(() => {
    const entries = Object.entries(data);
    const total = entries.reduce((sum, [, v]) => sum + v, 0);
    if (total === 0) return [];

    let angle = 0;
    return entries.map(([key, value]) => {
      const pct = value / total;
      const span = pct * 360;
      const slice: Slice = {
        key,
        label: key.charAt(0).toUpperCase() + key.slice(1),
        value,
        pct,
        start: angle,
        end: angle + span,
        palette: SOURCE_PALETTE[key] ?? FALLBACK,
      };
      angle += span;
      return slice;
    });
  }, [data]);

  // Sort back-to-front so front slices paint on top
  const sorted = useMemo(
    () =>
      [...slices].sort((a, b) => {
        const midA = ((a.start + a.end) / 2) % 360;
        const midB = ((b.start + b.end) / 2) % 360;
        return Math.abs(180 - midA) - Math.abs(180 - midB);
      }).reverse(),
    [slices],
  );

  if (slices.length === 0) return null;

  return (
    <Box>
      <Heading size="sm" mb={3}>
        Source Distribution
      </Heading>

      <Box position="relative">
        <svg
          viewBox="0 0 300 175"
          width="100%"
          style={{ maxWidth: 380, margin: '0 auto', display: 'block' }}
          role="img"
          aria-label="Source distribution donut chart"
        >
          <defs>
            {/* Per-slice gradient (top-left highlight → base color) */}
            {slices.map((s) => (
              <linearGradient
                key={`g-${s.key}`}
                id={`g-${s.key}`}
                x1="0" y1="0" x2="0.5" y2="1"
              >
                <stop offset="0%" stopColor={s.palette.light} />
                <stop offset="100%" stopColor={s.palette.base} />
              </linearGradient>
            ))}

            {/* Glossy top-face overlay */}
            <linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="white" stopOpacity="0.22" />
              <stop offset="45%" stopColor="white" stopOpacity="0.04" />
              <stop offset="100%" stopColor="black" stopOpacity="0.08" />
            </linearGradient>
          </defs>

          {/* Soft drop shadow */}
          <ellipse
            cx={CX}
            cy={CY + DEPTH + 14}
            rx={ORX * 0.85}
            ry={ORY * 0.45}
            fill={isDark ? 'rgba(0,0,0,0.45)' : 'rgba(0,0,0,0.1)'}
          />

          {/* 1) Outer walls (back → front) */}
          {sorted.map((s) => {
            const d = wallPath(s);
            if (!d) return null;
            return (
              <path
                key={`w-${s.key}`}
                d={d}
                fill={s.palette.dark}
                stroke={isDark ? 'rgba(0,0,0,0.35)' : 'rgba(0,0,0,0.12)'}
                strokeWidth={0.5}
                style={{
                  transition: 'opacity 0.2s ease',
                  opacity: hovered && hovered !== s.key ? 0.45 : 1,
                }}
                onMouseEnter={() => setHovered(s.key)}
                onMouseLeave={() => setHovered(null)}
                cursor="pointer"
              />
            );
          })}

          {/* 2) Top faces (back → front) */}
          {sorted.map((s) => (
            <g key={`t-${s.key}`}>
              {/* Colour fill */}
              <path
                d={topPath(s)}
                fill={`url(#g-${s.key})`}
                stroke={isDark ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.35)'}
                strokeWidth={0.5}
                style={{
                  transition: 'opacity 0.2s ease, filter 0.2s ease',
                  opacity: hovered && hovered !== s.key ? 0.45 : 1,
                  filter: hovered === s.key ? 'brightness(1.15)' : 'none',
                }}
                onMouseEnter={() => setHovered(s.key)}
                onMouseLeave={() => setHovered(null)}
                cursor="pointer"
              />
              {/* Gloss layer */}
              <path
                d={topPath(s)}
                fill="url(#gloss)"
                pointerEvents="none"
                style={{
                  transition: 'opacity 0.2s ease',
                  opacity: hovered && hovered !== s.key ? 0.25 : 0.55,
                }}
              />
            </g>
          ))}
        </svg>

        {/* Glassmorphism Tooltip */}
        {hovered && (() => {
          const s = slices.find((sl) => sl.key === hovered);
          if (!s) return null;
          return (
            <Box
              className="chart-tooltip"
              position="absolute"
              top="6px"
              right="6px"
              px={3}
              py={2}
              borderRadius="12px"
              pointerEvents="none"
              zIndex={5}
            >
              <Flex alignItems="center" gap={2}>
                <Box w={2.5} h={2.5} borderRadius="full" bg={s.palette.base} />
                <Text fontWeight="600" fontSize="sm">{s.label}</Text>
              </Flex>
              <Text className="chart-tooltip-sub" fontSize="xs" mt={0.5}>
                {s.value} sources &middot; {(s.pct * 100).toFixed(0)}%
              </Text>
            </Box>
          );
        })()}
      </Box>

      {/* Interactive Legend */}
      <Flex justifyContent="center" gap={5} mt={3} flexWrap="wrap">
        {slices.map((s) => (
          <Flex
            key={s.key}
            alignItems="center"
            gap={1.5}
            cursor="pointer"
            opacity={hovered && hovered !== s.key ? 0.5 : 1}
            transition="opacity 0.2s ease"
            onMouseEnter={() => setHovered(s.key)}
            onMouseLeave={() => setHovered(null)}
          >
            <Box
              w={2.5}
              h={2.5}
              borderRadius="full"
              bg={s.palette.base}
              boxShadow={`0 0 6px ${s.palette.base}55`}
            />
            <Text fontSize="sm" fontWeight="500">{s.label}</Text>
            <Text fontSize="xs" color="fg.muted">{(s.pct * 100).toFixed(0)}%</Text>
          </Flex>
        ))}
      </Flex>
    </Box>
  );
}
