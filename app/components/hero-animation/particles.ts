import * as THREE from "three";
import gsap from "gsap";

export interface ParticleSystem {
  points: THREE.Points;
  timeline: gsap.core.Timeline;
  reset: () => void;
  dispose: () => void;
}

// Generate soft radial glow texture dynamically on canvas
function createGlowTexture(): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext("2d")!;

  const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, "rgba(255, 255, 255, 1.0)");
  gradient.addColorStop(0.3, "rgba(155, 127, 246, 0.8)"); // #9B7FF6 Purple core
  gradient.addColorStop(0.7, "rgba(155, 127, 246, 0.2)");
  gradient.addColorStop(1, "rgba(0, 0, 0, 0)");

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 64, 64);

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

export function createParticleSystem(): ParticleSystem {
  const particleCount = 140;
  const geometry = new THREE.BufferGeometry();
  const basePositions = new Float32Array(particleCount * 3);
  const currentPositions = new Float32Array(particleCount * 3);
  const driftVelocities = new Float32Array(particleCount);
  const scales = new Float32Array(particleCount);

  for (let i = 0; i < particleCount; i++) {
    const idx = i * 3;
    const angle = Math.random() * Math.PI * 2;
    const radius = 0.3 + Math.random() * 1.8;
    const x = Math.cos(angle) * radius + (Math.random() - 0.5) * 0.3;
    const y = -0.2 + Math.random() * 0.8;
    const z = Math.sin(angle) * radius + (Math.random() - 0.5) * 0.3;

    basePositions[idx] = x;
    basePositions[idx + 1] = y;
    basePositions[idx + 2] = z;

    currentPositions[idx] = x;
    currentPositions[idx + 1] = y;
    currentPositions[idx + 2] = z;

    driftVelocities[i] = 0.4 + Math.random() * 0.6;
    scales[i] = 0.5 + Math.random() * 1.5;
  }

  geometry.setAttribute("position", new THREE.BufferAttribute(currentPositions, 3));

  const texture = createGlowTexture();
  const material = new THREE.PointsMaterial({
    size: 0.12,
    map: texture,
    transparent: true,
    opacity: 0,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  const points = new THREE.Points(geometry, material);
  points.visible = false;

  const proxy = { progress: 0, opacity: 0 };

  const resetPositions = () => {
    for (let i = 0; i < particleCount * 3; i++) {
      currentPositions[i] = basePositions[i];
    }
    geometry.attributes.position.needsUpdate = true;
    material.opacity = 0;
    points.visible = false;
    proxy.progress = 0;
    proxy.opacity = 0;
  };

  const particleTimeline = gsap.timeline({
    paused: true,
    onStart: () => {
      points.visible = true;
    },
    onComplete: () => {
      points.visible = false;
    },
  });

  particleTimeline.to(
    proxy,
    {
      opacity: 0.85,
      duration: 0.4,
      ease: "power2.out",
      onUpdate: () => {
        material.opacity = proxy.opacity;
      },
    },
    0
  );

  particleTimeline.to(
    proxy,
    {
      progress: 1,
      duration: 1.6,
      ease: "power1.out",
      onUpdate: () => {
        const p = proxy.progress;
        for (let i = 0; i < particleCount; i++) {
          const idx = i * 3;
          currentPositions[idx + 1] = basePositions[idx + 1] + driftVelocities[i] * p;
          currentPositions[idx] = basePositions[idx] + Math.sin(p * Math.PI * 2 + i) * 0.05;
        }
        geometry.attributes.position.needsUpdate = true;
      },
    },
    0
  );

  particleTimeline.to(
    proxy,
    {
      opacity: 0,
      duration: 0.4,
      ease: "power2.in",
      onUpdate: () => {
        material.opacity = proxy.opacity;
      },
    },
    1.2
  );

  const dispose = () => {
    particleTimeline.kill();
    geometry.dispose();
    material.dispose();
    texture.dispose();
  };

  return {
    points,
    timeline: particleTimeline,
    reset: resetPositions,
    dispose,
  };
}
