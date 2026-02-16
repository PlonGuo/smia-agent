import { useRef, useMemo, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { createNoise3D } from 'simplex-noise';

const SPHERE_RADIUS = 1.5;
const ICOSA_DETAIL = 12;
const NOISE_SPEED = 0.3;
const NOISE_AMPLITUDE = 0.08;
const NOISE_FREQUENCY = 2.0;
const ROTATION_SPEED = 0.15;
const MOUSE_SENSITIVITY = 0.6;
const LERP_FACTOR = 0.05;
const RIPPLE_RADIUS = 1.2;
const RIPPLE_STRENGTH = 0.35;
const DASH_ASPECT_RATIO = 3.0;
const POINT_BASE_SIZE = 22.0;

const vertexShader = /* glsl */ `
  uniform float uPixelRatio;
  attribute vec3 color;
  attribute float aRotation;
  varying vec3 vColor;
  varying float vRotation;

  void main() {
    vColor = color;
    vRotation = aRotation;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = ${POINT_BASE_SIZE.toFixed(1)} * uPixelRatio * (1.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const fragmentShader = /* glsl */ `
  varying vec3 vColor;
  varying float vRotation;

  void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float c = cos(vRotation);
    float s = sin(vRotation);
    vec2 rotUV = vec2(uv.x * c - uv.y * s, uv.x * s + uv.y * c);

    // Elongated ellipse (short dash shape)
    float dist = length(vec2(rotUV.x * ${DASH_ASPECT_RATIO.toFixed(1)}, rotUV.y));
    float alpha = 1.0 - smoothstep(0.3, 0.5, dist);

    if (alpha < 0.01) discard;

    gl_FragColor = vec4(vColor, alpha * 0.9);
  }
`;

export default function ParticleSphere() {
  const pointsRef = useRef<THREE.Points>(null);
  const idleAngle = useRef({ x: 0, y: 0 });
  const noise3D = useMemo(() => createNoise3D(), []);

  // Track mouse globally — canvas is behind content overlay so R3F pointer doesn't update
  const mouseNDC = useMemo(() => new THREE.Vector2(0, 0), []);
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      mouseNDC.x = (e.clientX / window.innerWidth) * 2 - 1;
      mouseNDC.y = -(e.clientY / window.innerHeight) * 2 + 1;
    };
    window.addEventListener('mousemove', onMouseMove);
    return () => window.removeEventListener('mousemove', onMouseMove);
  }, [mouseNDC]);

  // Pre-allocate objects for hot loop (avoid GC)
  const raycaster = useMemo(() => new THREE.Raycaster(), []);
  const hitPoint = useMemo(() => new THREE.Vector3(), []);
  const localHitPoint = useMemo(() => new THREE.Vector3(), []);
  const boundingSphere = useMemo(
    () => new THREE.Sphere(new THREE.Vector3(0, 0, 0), SPHERE_RADIUS),
    []
  );
  const inverseMatrix = useMemo(() => new THREE.Matrix4(), []);

  const { basePositions, colors, rotations, count } = useMemo(() => {
    const geo = new THREE.IcosahedronGeometry(SPHERE_RADIUS, ICOSA_DETAIL);
    const pos = geo.attributes.position;
    const count = pos.count;

    const base = new Float32Array(pos.array);
    const colorArray = new Float32Array(count * 3);
    const rotArray = new Float32Array(count);
    const brightGreen = new THREE.Color('#4ade80');
    const darkGreen = new THREE.Color('#166534');

    for (let i = 0; i < count; i++) {
      const y = pos.getY(i);
      const t = (y + SPHERE_RADIUS) / (SPHERE_RADIUS * 2);
      const color = new THREE.Color().lerpColors(darkGreen, brightGreen, t);
      colorArray[i * 3] = color.r;
      colorArray[i * 3 + 1] = color.g;
      colorArray[i * 3 + 2] = color.b;
      rotArray[i] = Math.random() * Math.PI * 2;
    }

    geo.dispose();
    return { basePositions: base, colors: colorArray, rotations: rotArray, count };
  }, []);

  const positions = useMemo(() => new Float32Array(basePositions), [basePositions]);

  const { gl } = useThree();

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        transparent: true,
        depthWrite: false,
        uniforms: {
          uPixelRatio: { value: gl.getPixelRatio() },
        },
      }),
    [gl]
  );

  useFrame((state) => {
    if (!pointsRef.current) return;

    const time = state.clock.elapsedTime;

    // Raycast mouse onto the sphere to find the "impact" point
    raycaster.setFromCamera(mouseNDC, state.camera);
    const intersection = raycaster.ray.intersectSphere(boundingSphere, hitPoint);

    // Transform hit point into the mesh's local space (accounts for rotation)
    let hasHit = false;
    if (intersection) {
      inverseMatrix.copy(pointsRef.current.matrixWorld).invert();
      localHitPoint.copy(hitPoint).applyMatrix4(inverseMatrix);
      hasHit = true;
    }

    for (let i = 0; i < count; i++) {
      const bx = basePositions[i * 3];
      const by = basePositions[i * 3 + 1];
      const bz = basePositions[i * 3 + 2];

      const len = Math.sqrt(bx * bx + by * by + bz * bz);
      const nx = bx / len;
      const ny = by / len;
      const nz = bz / len;

      const noiseVal = noise3D(
        bx * NOISE_FREQUENCY + time * NOISE_SPEED,
        by * NOISE_FREQUENCY + time * NOISE_SPEED,
        bz * NOISE_FREQUENCY + time * NOISE_SPEED
      );

      let dispX = nx * noiseVal * NOISE_AMPLITUDE;
      let dispY = ny * noiseVal * NOISE_AMPLITUDE;
      let dispZ = nz * noiseVal * NOISE_AMPLITUDE;

      // Ripple spread — particles near cursor spread tangentially like a stone in water
      if (hasHit) {
        const dx = bx - localHitPoint.x;
        const dy = by - localHitPoint.y;
        const dz = bz - localHitPoint.z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

        if (dist < RIPPLE_RADIUS && dist > 0.001) {
          // Project (particle - hitPoint) onto tangent plane at particle position
          const dotPN = dx * nx + dy * ny + dz * nz;
          let tx = dx - dotPN * nx;
          let ty = dy - dotPN * ny;
          let tz = dz - dotPN * nz;

          // Normalize tangent direction
          const tLen = Math.sqrt(tx * tx + ty * ty + tz * tz);
          if (tLen > 0.001) {
            tx /= tLen;
            ty /= tLen;
            tz /= tLen;

            // Smooth falloff: strongest at center, fades to edge
            const falloff = 1.0 - (dist / RIPPLE_RADIUS);
            const strength = falloff * falloff * RIPPLE_STRENGTH;

            dispX += tx * strength;
            dispY += ty * strength;
            dispZ += tz * strength;
          }
        }
      }

      positions[i * 3] = bx + dispX;
      positions[i * 3 + 1] = by + dispY;
      positions[i * 3 + 2] = bz + dispZ;
    }

    const posAttr = pointsRef.current.geometry.attributes.position;
    if (posAttr instanceof THREE.BufferAttribute) {
      posAttr.needsUpdate = true;
    }

    // Accumulate idle rotation separately
    idleAngle.current.y += ROTATION_SPEED * 0.01;
    idleAngle.current.x += ROTATION_SPEED * 0.003;

    // Compose idle rotation + mouse tilt (lerped smoothly)
    const targetX = mouseNDC.y * MOUSE_SENSITIVITY + idleAngle.current.x;
    const targetY = mouseNDC.x * MOUSE_SENSITIVITY + idleAngle.current.y;
    const mesh = pointsRef.current;
    mesh.rotation.x += (targetX - mesh.rotation.x) * LERP_FACTOR;
    mesh.rotation.y += (targetY - mesh.rotation.y) * LERP_FACTOR;
  });

  return (
    <points ref={pointsRef} material={material} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
        <bufferAttribute attach="attributes-aRotation" args={[rotations, 1]} />
      </bufferGeometry>
    </points>
  );
}
