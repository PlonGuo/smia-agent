# Role & Context

Act as a Senior Creative Developer and UI/UX Expert specializing in WebGL and React.
I am building the frontend for my "Social Media Intelligence Agent" (SmIA). I need you to design and implement a stunning, futuristic "Hero Section" that serves as the main entry point for the user.

# The Goal

Create a "Gemini-style" interactive 3D background featuring a **Floating Particle Sphere** that acts as the visual representation of the Agent's "Brain". It must be visually immersive, responsive to mouse interaction, and aesthetically aligned with a modern AI product.

# Tech Stack Requirements

- **Framework**: React (Next.js App Router compatible)
- **Styling**: Tailwind CSS
- **3D Library**: @react-three/fiber (R3F)
- **3D Helpers**: @react-three/drei
- **Animation**: Framer Motion (for UI elements entry)
- **Logic**: Custom Hooks for mouse tracking

# Visual & Technical Specifications (Crucial)

## 1. The 3D Scene (The Brain)

- **Geometry**: Use an `IcosahedronGeometry` or a high-segment `SphereGeometry` as the base.
- **Material**: Do NOT use a solid mesh. Use `PointsMaterial` or a custom `ShaderMaterial` to render it as thousands of tiny, glowing particles.
- **Color Palette**: Deep Space Blue (#0B0F19) for the background. The particles should use a gradient ranging from Electric Cyan (#00F0FF) to Deep Purple (#7000FF).
- **Movement (The "Alive" Factor)**:
  - **Idle Animation**: The sphere should slowly rotate on multiple axes.
  - **Wave Effect**: (Advanced) If possible, use Simplex Noise in the vertex shader or update vertex positions in `useFrame` to make the sphere surface "undulate" or "breathe" slightly, like a living organism.
  - **Mouse Interaction**: The sphere should slightly rotate or tilt towards the user's cursor position.

## 2. Post-Processing (The "Glow")

- Implement a "Bloom" effect (using `@react-three/postprocessing`) to make the particles glow, giving it that high-tech, ethereal AI look.

## 3. The UI Overlay (Glassmorphism)

- Overlay the 3D scene with a clean, centered UI.
- **Container**: A frosted glass card (backdrop-filter: blur) that holds the text and input.
- **Typography**: Modern sans-serif (Inter or similar). Title: "SmIA Intelligence".
- **Input Field**: A high-quality search bar that says "Ask me to research a URL..." with a subtle glow on focus.

# Implementation Guide

Please provide the complete code in a single file (or split if necessary) including:

1. The `Scene` component (Canvas setup).
2. The `ParticleSphere` component (The math and mesh).
3. The `Overlay` component (The Tailwind UI).
4. Handle `window.resize` gracefully.
5. Ensure performance optimization (use `instancedMesh` if particle count > 5000, or simple `Points` if < 5000).

Let's build something world-class. Start by explaining your approach, then show the code.
