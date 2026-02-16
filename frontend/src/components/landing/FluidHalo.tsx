import { useEffect } from 'react';
import { Box } from '@chakra-ui/react';

const keyframesStyles = `
  @keyframes drift1 {
    0%, 100% { transform: translate(0%, 0%) scale(1); opacity: 0.6; }
    25% { transform: translate(10%, -15%) scale(1.1); opacity: 0.8; }
    50% { transform: translate(-5%, 10%) scale(0.95); opacity: 0.5; }
    75% { transform: translate(-10%, -5%) scale(1.05); opacity: 0.7; }
  }
  @keyframes drift2 {
    0%, 100% { transform: translate(0%, 0%) scale(1); opacity: 0.5; }
    33% { transform: translate(-15%, 10%) scale(1.15); opacity: 0.7; }
    66% { transform: translate(10%, -10%) scale(0.9); opacity: 0.4; }
  }
  @keyframes drift3 {
    0%, 100% { transform: translate(0%, 0%) scale(1.05); opacity: 0.4; }
    20% { transform: translate(15%, 5%) scale(0.95); opacity: 0.6; }
    50% { transform: translate(-10%, -15%) scale(1.1); opacity: 0.3; }
    80% { transform: translate(5%, 10%) scale(1); opacity: 0.5; }
  }
  @keyframes drift4 {
    0%, 100% { transform: translate(0%, 0%) scale(1); opacity: 0.35; }
    30% { transform: translate(-8%, -12%) scale(1.08); opacity: 0.55; }
    60% { transform: translate(12%, 8%) scale(0.92); opacity: 0.3; }
  }
`;

export default function FluidHalo() {
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = keyframesStyles;
    document.head.appendChild(style);
    return () => { document.head.removeChild(style); };
  }, []);

  return (
    <Box position="absolute" inset={0} zIndex={0} overflow="hidden">

      {/* Blob 1 — large bright green, upper area */}
      <Box
        position="absolute"
        top="-20%"
        left="-10%"
        width="70%"
        height="70%"
        borderRadius="50%"
        background="radial-gradient(circle, #4ade80 0%, #22c55e 30%, transparent 70%)"
        filter="blur(100px)"
        opacity={0.6}
        style={{ animation: 'drift1 16s ease-in-out infinite' }}
      />

      {/* Blob 2 — deep green, lower right */}
      <Box
        position="absolute"
        bottom="-15%"
        right="-10%"
        width="60%"
        height="60%"
        borderRadius="50%"
        background="radial-gradient(circle, #166534 0%, #052e16 40%, transparent 70%)"
        filter="blur(90px)"
        opacity={0.5}
        style={{ animation: 'drift2 20s ease-in-out infinite' }}
      />

      {/* Blob 3 — medium green, center-left */}
      <Box
        position="absolute"
        top="30%"
        left="20%"
        width="50%"
        height="50%"
        borderRadius="50%"
        background="radial-gradient(circle, #22c55e 0%, #166534 35%, transparent 70%)"
        filter="blur(80px)"
        opacity={0.4}
        style={{ animation: 'drift3 14s ease-in-out infinite' }}
      />

      {/* Blob 4 — dark anchor, keeps edges dark */}
      <Box
        position="absolute"
        top="10%"
        right="5%"
        width="55%"
        height="55%"
        borderRadius="50%"
        background="radial-gradient(circle, #052e16 0%, rgba(0,0,0,0.8) 50%, transparent 70%)"
        filter="blur(90px)"
        opacity={0.35}
        style={{ animation: 'drift4 18s ease-in-out infinite' }}
      />

      {/* Dark vignette overlay to keep edges dark */}
      <Box
        position="absolute"
        inset={0}
        background="radial-gradient(ellipse at 50% 50%, transparent 0%, rgba(0,0,0,0.4) 50%, rgba(0,0,0,0.8) 100%)"
      />
    </Box>
  );
}
