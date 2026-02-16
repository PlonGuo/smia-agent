# Landing Page 3D Background Upgrade — Design Doc

**Date**: 2026-02-15
**Status**: Approved

## Goal

Replace the current 2D Matrix canvas animation on the landing page with a 3D interactive particle sphere, fluid green-dark halo background, and glassmorphism UI treatment. Keep all existing content and auth flow unchanged.

## What Changes

| Aspect | Current | New |
|--------|---------|-----|
| Background | 2D Canvas Matrix falling symbols | Fluid green-dark gradient halo (CSS) + 3D particle sphere (WebGL) |
| Glow effect | None | Bloom post-processing (green tint) |
| Mouse interaction | None | Sphere tilts toward cursor |
| UI styling | Solid dark background cards | Glassmorphism (frosted glass) on feature cards |
| Entry animations | None | Framer Motion fade-in / slide-up |

## What Stays the Same

- All text content, CTA buttons, feature cards
- Auth flow (Get Started -> Signup, Sign In -> Login)
- Conditional rendering (logged-in vs logged-out CTAs)
- Page routing, Layout component, nav bar

## Visual Layers (back to front)

1. **Black base** (`#000000`)
2. **Fluid halo**: Overlapping soft radial gradients blending green (`#4ade80`, `#22c55e`) into dark (`#000`, `#0a0a0a`). Animated with slow transform shifts and heavy blur (80px+). No hard edges — smooth color diffusion like ink in water.
3. **3D particle sphere**: R3F Canvas with `alpha: true` (transparent) so halo shows through. Green-toned particles with bloom glow.
4. **UI overlay**: Existing hero text, buttons, and feature cards with glassmorphism treatment.

## Color Palette

- Background: `#000000` / `#0a0a0a`
- Particles bright: `#4ade80` (green-400)
- Particles dark: `#166534` (green-800)
- Halo greens: `#4ade80`, `#22c55e`, `#052e16`
- Bloom: Green tint
- Glassmorphism borders: Green-tinted, semi-transparent

## New Dependencies

```
@react-three/fiber          — React renderer for Three.js
@react-three/drei           — R3F helpers
@react-three/postprocessing — Bloom effect
three                       — Three.js core
simplex-noise               — Vertex displacement for sphere "breathing"
```

## Component Architecture

```
Home.tsx (updated)
├── FluidHalo (new) — CSS animated gradient background
│   └── Multiple <div>s with radial gradients, blur, keyframe animations
├── ParticleScene (new) — lazy-loaded via React.lazy + Suspense
│   ├── <Canvas alpha={true}> with camera setup
│   ├── <ParticleSphere />
│   │   ├── IcosahedronGeometry rendered as <Points>
│   │   ├── Custom color attribute (green gradient)
│   │   └── useFrame: rotation + simplex noise displacement + mouse tilt
│   └── <EffectComposer> + <Bloom />
├── HeroOverlay (extracted from current Home.tsx)
│   ├── Glassmorphism container (backdrop-filter: blur)
│   ├── Title + subtitle (existing content)
│   ├── CTA buttons (existing)
│   └── Framer Motion entry animations
└── FeatureCards (extracted, glassmorphism styling)
```

## Particle Sphere Spec

- Geometry: `IcosahedronGeometry(1, 12)` (~3000 vertices)
- Render: `<Points>` with `<PointsMaterial>` (size ~0.015, sizeAttenuation)
- Color: Per-vertex color attribute, gradient from `#4ade80` to `#166534`
- Idle: Slow rotation on Y and X axes
- Breathing: Simplex noise applied to vertex positions in `useFrame`, creating organic surface undulation
- Mouse: Sphere tilts toward cursor (tracked via `onPointerMove` on Canvas)
- Bloom: Intensity ~1.5, threshold ~0.2, luminanceSmoothing ~0.9

## Performance

- Lazy-load entire `<Canvas>` so Three.js bundle only loads on landing page
- `<Suspense>` fallback: static gradient matching the halo
- WebGL check: fallback to halo-only background if WebGL unavailable
- Particle count ~3000 (uses simple `<Points>`, no instancing needed)

## Risk Mitigation

- Bundle size: Lazy loading isolates Three.js to landing page only
- Low-end devices: Halo effect alone looks good as fallback
- No SSR concerns (Vite SPA)
