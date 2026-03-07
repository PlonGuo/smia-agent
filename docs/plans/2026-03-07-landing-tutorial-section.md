# Plan: Landing Page Tutorial Section

## Context
The landing page is currently a single-viewport hero with no scrollable content below. Users land on the page but have no guidance on how to use SmIA's features (Analyze, AI Digest, Telegram). Adding a slide-style tutorial section below the hero will onboard new users and showcase the product's capabilities with a premium, presentation-like scroll experience.

## Design Decisions
- **Slide-style layout**: Each feature gets its own section with alternating mockup/text placement
- **Free scroll + animations**: No scroll-snap. Natural scrolling with Framer Motion `whileInView` animations creating the presentation feel
- **Scroll cue**: Subtle bouncing chevron at bottom of hero (low opacity, delayed appearance, respects reduced-motion)
- **Slide separation**: Large faded step numbers ("01", "02", "03") as watermark behind each slide
- **Keep both sections**: Existing feature highlight cards stay in hero; tutorial slides are separate below
- **Differentiated styling**: Tutorial slides use distinct visual treatment from hero's glassmorphic cards (solid dark bg + green left border)
- **Outcome-oriented copy**: Frame steps around user value, not mechanical instructions
- **Closing CTA**: "Ready to get started?" section after the last slide with auth-aware buttons
- **Mockups**: Styled placeholder boxes (replaceable with real screenshots later)
- **`overflowX="hidden"`** on each slide to prevent horizontal scrollbar flash during slide-in animations

## Image Storage
- Store tutorial screenshots in `frontend/public/images/` (committed to git)
- Reference as `/images/analyze.png`, `/images/digest.png`, `/images/telegram.png`
- Initially use styled placeholders; swap for real `.png` files later
- **Aspect-ratio container**: `aspectRatio="16/9"` with `overflow="hidden"` — adapts to different screenshot shapes
- When real images arrive: add `loading="lazy"` and explicit `width`/`height` attributes

## Files to Modify/Create

| File | Action |
|------|--------|
| `frontend/src/components/landing/TutorialSection.tsx` | **Create** — slide-style tutorial component with closing CTA |
| `frontend/src/components/landing/CTAButtons.tsx` | **Create** — shared auth-aware CTA buttons (used by hero + closing CTA) |
| `frontend/src/pages/Home.tsx` | **Modify** — restructure for scrollability, add scroll chevron, import TutorialSection, use CTAButtons |
| `frontend/src/components/landing/ParticleScene.tsx` | **Modify** — add IntersectionObserver to pause render loop when off-screen, pass `visible` ref to ParticleSphere |
| `frontend/src/components/landing/ParticleSphere.tsx` | **Modify** — accept `visible` ref prop, skip `useFrame` computation when not visible |
| `frontend/public/images/` | **Create folder** — for tutorial screenshot assets |

## Implementation Steps

### 1. Create branch `feature/landing-tutorial`
From `development` branch.

### 2. Create `TutorialSection.tsx`
New component at `frontend/src/components/landing/TutorialSection.tsx`:

**Structure**: Section heading + 3 full-width slides + closing CTA:

```
"How It Works" heading
Slide 1: [Mockup LEFT]  [Text RIGHT]   — Analyze   (faded "01" watermark)
Slide 2: [Text LEFT]    [Mockup RIGHT]  — Digest   (faded "02" watermark)
Slide 3: [Mockup LEFT]  [Text RIGHT]   — Telegram  (faded "03" watermark)
"Ready to get started?" + CTA buttons
```

- **Semantic HTML**: Wrap in `<section aria-labelledby="tutorial-heading">`, steps in `<ol>`
- **Section heading**: "How It Works" as `<Heading as="h2">` with `whileInView` fade-in
- **3 slides** rendered via `.map()` with alternating `flexDirection`:

**Slide 1 — Analyze a Topic** (icon: `Search`)
1. Ask about any topic, product, or trend
2. We crawl Reddit, YouTube, and Amazon for real-time data
3. Get a structured intelligence report with sentiment analysis

**Slide 2 — AI Daily Digest** (icon: `Newspaper`)
1. Open the AI Digest page from the sidebar
2. View today's auto-generated intelligence briefing
3. Share or export the digest as an image

**Slide 3 — Connect Telegram** (icon: `Send`)
1. Generate a bind code from Settings
2. Send `/bind YOUR_CODE` to @SmIA_bot on Telegram
3. Get analysis and digests delivered straight to Telegram

**Per-slide layout**:
- `Flex direction={{ base: "column", md: index % 2 === 0 ? "row" : "row-reverse" }}` (alternating)
- `position="relative"` (for watermark number positioning)
- `minH={{ base: "auto", md: "70vh" }}`, `alignItems="center"`, `gap={{ base: 8, md: 16 }}`
- `overflowX="hidden"` to prevent horizontal scrollbar during x-axis animations
- Each side takes ~50% width on desktop, full width stacked on mobile

**Large faded step number** (watermark per slide):
- `position="absolute"`, `top="50%"`, `left={{ base: "50%", md: "5%" }}`, `transform="translateY(-50%)"`
- `fontSize={{ base: "8rem", md: "12rem" }}`, `fontWeight="bold"`
- `color="rgba(74, 222, 128, 0.06)"` — very faint green watermark
- `pointerEvents="none"`, `userSelect="none"`, `aria-hidden="true"`
- `display={{ base: "none", md: "block" }}` — hidden on mobile to avoid overlapping stacked content
- Content: "01", "02", "03"

**Text side styling**:
- Number badge: `bg="green.400"`, `color="black"`, `w="36px"`, `h="36px"`, circle with step number
- Feature title: `Heading size="xl" color="white"`
- Lucide icon in `green.400` next to title
- Steps as `<ol>` with `Text color="gray.300" fontSize="md"` — generous line spacing
- Green left accent line on the text container: `borderLeft="3px solid"`, `borderLeftColor="green.400"`

**Mockup side styling**:
- `aspectRatio="16/9"`, `overflow="hidden"`, `borderRadius="xl"`
- `bg="rgba(74, 222, 128, 0.05)"`, `border="1px solid rgba(74, 222, 128, 0.1)"`
- Initially: centered placeholder label with feature icon in `gray.600`
- Later: `<Image src="/images/{feature}.png" objectFit="cover" loading="lazy" />`
- `maxW={{ base: "100%", md: "50%" }}`, `w="100%"`

**Scroll animations per slide** (staggered children, Framer Motion `whileInView`):
- Mockup: `initial={{ opacity: 0, x: -40 }}` → `whileInView={{ opacity: 1, x: 0 }}` (slides in from side)
- For reversed slides (index odd), mockup slides from right (`x: 40`)
- Title: `initial={{ opacity: 0, y: 20 }}` → fade up, delay 0.1
- Steps: staggered fade up, delay 0.1 each
- `viewport={{ once: true, margin: "-100px" }}`

**Closing CTA section** (after the last slide):
- `py={{ base: 16, md: 24 }}`, centered, `whileInView` fade-in
- `Heading size="xl" color="white"`: "Ready to get started?"
- Extract a shared `<CTAButtons />` component (used by both hero and closing CTA) to avoid duplicating the auth-aware conditional rendering logic
- Uses `useAuth()` hook, `.btn-silicone` and `.btn-crystal` CSS classes

**Section padding**: `py={{ base: 12, md: 0 }}`, `px={{ base: 6, md: 12 }}`, `maxW="6xl"`, `mx="auto"`

### 3. Modify `Home.tsx`
- **Restructure outer Box**: Keep hero at `minH="100dvh"` with `overflow="hidden"` to clip particles/halo
- Wrap hero + TutorialSection in a parent `Box bg="black"`
- **Add scroll chevron** at the bottom of the hero Flex:
  - `ChevronDown` from Lucide, `position="absolute"`, `bottom={6}`
  - Subtle styling: `color="gray.500"`, `opacity={0.4}`, `size={20}`
  - Bounce animation: `animate={{ y: [0, 6, 0] }}`, `transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}`
  - Delayed appearance: `initial={{ opacity: 0 }}`, `animate={{ opacity: 0.4 }}`, `transition={{ delay: 1.5 }}`
  - `aria-hidden="true"` (decorative indicator)
  - Respects `prefers-reduced-motion`: add CSS `@media (prefers-reduced-motion: reduce) { animation: none; }` or use Framer Motion's built-in support
- **Import and render** `<TutorialSection />` below the hero Box

### 4. Add IntersectionObserver to ParticleScene (not ParticleSphere)
- In `ParticleScene.tsx`, add a `useRef<boolean>(true)` for visibility tracking
- Attach `IntersectionObserver` to the canvas wrapper div in `useEffect`
- Pass the `visible` ref as a prop to `<ParticleSphere visible={visibleRef} />`
- In `ParticleSphere.tsx`: accept the `visible` ref prop, early return in `useFrame` when `visible.current === false`
- This prevents burning GPU cycles when user has scrolled to tutorial slides

### 5. Test & verify
- Check slide layout alternates correctly (mockup left/right/left)
- Verify faded step numbers ("01", "02", "03") are visible but non-intrusive
- Verify free scroll feels natural
- Verify scroll chevron appears with delay at hero bottom, bounces subtly
- Verify per-slide animations trigger correctly with staggered children
- Verify no horizontal scrollbar appears during slide-in animations
- Verify closing CTA shows correct buttons based on auth state
- Verify mobile: slides stack vertically, mockup above text
- Verify particle render loop pauses when scrolled past
- Verify color contrast meets WCAG AA
- `cd frontend && pnpm dev` and visually confirm

## Verification
1. `cd frontend && pnpm dev` — start dev server
2. Visit landing page — hero unchanged, subtle chevron bounces at bottom
3. Scroll down — "How It Works" heading fades in, slides animate with staggered reveals
4. Verify alternating layout: slide 1 (mockup left), slide 2 (mockup right), slide 3 (mockup left)
5. Verify faded watermark numbers behind each slide
6. Verify closing CTA section appears after last slide with correct auth-aware buttons
7. Check mobile viewport — slides stack vertically, chevron visible
8. Particles/halo stay contained in hero section
9. DevTools Performance tab — confirm particle loop pauses when scrolled past
