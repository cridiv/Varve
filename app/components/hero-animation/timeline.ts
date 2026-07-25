import * as THREE from "three";
import gsap from "gsap";
import { CoreLayers } from "./core-layers";
import { ParticleSystem } from "./particles";
import { SceneSetup } from "./scene";

export interface AnimationTimeline {
  mainTimeline: gsap.core.Timeline;
  backgroundSpin: gsap.core.Tween;
  dispose: () => void;
}

export function createAnimationTimeline(
  coreLayers: CoreLayers,
  particleSystem: ParticleSystem,
  sceneSetup: SceneSetup,
  onUpdateCallback?: () => void
): AnimationTimeline {
  const { coreGroup, layers, mainMeshes, glowRings } = coreLayers;
  const { accentPointLight } = sceneSetup;

  // 6.1 — Continuous Background Rotation (independent 22s linear spin)
  const backgroundSpin = gsap.to(coreGroup.rotation, {
    y: Math.PI * 2,
    duration: 22,
    repeat: -1,
    ease: "none",
  });

  // 6.2 — Main Seamless Explode/Reform Loop (9s loop)
  const mainTimeline = gsap.timeline({
    repeat: -1,
    defaults: { ease: "power2.inOut" },
    onUpdate: onUpdateCallback,
  });

  const layer1 = layers.get("layer-1")!;
  const layer2 = layers.get("layer-2")!;
  const layer3 = layers.get("layer-3")!;
  const layer4 = layers.get("layer-4")!;
  const layer5 = layers.get("layer-5")!;

  const mainMesh3 = mainMeshes.get("layer-3")!;

  const purpleEmissiveColor = new THREE.Color("#9B7FF6");

  const emissiveProxies = {
    layer3Intensity: 0,
    pointLightIntensity: 0,
  };

  // Base assembled positions
  const base1Y = 1.16;
  const base2Y = 0.58;
  const base3Y = 0;
  const base4Y = -0.58;
  const base5Y = -1.16;

  // --- Phase A: 0.0s – 1.0s: Fluid Assembled Breathing Motion ---
  // Subtle organic floating wave at assembled state (matches 8.0s -> 9.0s seamlessly)
  mainTimeline.to(
    layer1.position,
    { y: base1Y + 0.04, duration: 1.0, ease: "sine.inOut" },
    0
  );
  mainTimeline.to(
    layer2.position,
    { y: base2Y + 0.02, duration: 1.0, ease: "sine.inOut" },
    0
  );
  mainTimeline.to(
    layer3.position,
    { y: base3Y, duration: 1.0, ease: "sine.inOut" },
    0
  );
  mainTimeline.to(
    layer4.position,
    { y: base4Y - 0.02, duration: 1.0, ease: "sine.inOut" },
    0
  );
  mainTimeline.to(
    layer5.position,
    { y: base5Y - 0.04, duration: 1.0, ease: "sine.inOut" },
    0
  );

  // --- Phase B: 1.0s – 3.0s: Smooth Explode Outward ---
  mainTimeline.to(
    layer1.position,
    { x: -1.4, y: 2.6, z: 0.4, duration: 2.0, ease: "power2.inOut" },
    1.0
  );
  mainTimeline.to(
    layer1.rotation,
    { z: 0.15, x: 0.08, duration: 2.0, ease: "power2.inOut" },
    1.0
  );

  mainTimeline.to(
    layer2.position,
    { x: 1.3, y: 1.5, z: -0.3, duration: 2.0, ease: "power2.inOut" },
    1.0
  );
  mainTimeline.to(
    layer2.rotation,
    { z: -0.1, x: -0.06, duration: 2.0, ease: "power2.inOut" },
    1.0
  );

  // Center layer hover float
  mainTimeline.to(
    layer3.position,
    { y: 0.06, duration: 1.0, yoyo: true, repeat: 1, ease: "sine.inOut" },
    1.0
  );

  mainTimeline.to(
    layer4.position,
    { x: -1.3, y: -1.5, z: -0.3, duration: 2.0, ease: "power2.inOut" },
    1.0
  );
  mainTimeline.to(
    layer4.rotation,
    { z: 0.1, x: 0.05, duration: 2.0, ease: "power2.inOut" },
    1.0
  );

  mainTimeline.to(
    layer5.position,
    { x: 1.4, y: -2.6, z: 0.4, duration: 2.0, ease: "power2.inOut" },
    1.0
  );
  mainTimeline.to(
    layer5.rotation,
    { z: -0.15, x: -0.08, duration: 2.0, ease: "power2.inOut" },
    1.0
  );

  // --- Phase C: 3.0s – 5.0s: Held Apart & Layer-3 Purple Pulse ---
  mainTimeline.to(
    emissiveProxies,
    {
      layer3Intensity: 1.0,
      pointLightIntensity: 3.5,
      duration: 1.0,
      ease: "sine.inOut",
      onUpdate: () => {
        mainMesh3.material.emissive.copy(purpleEmissiveColor);
        mainMesh3.material.emissiveIntensity = emissiveProxies.layer3Intensity;
        accentPointLight.intensity = emissiveProxies.pointLightIntensity;

        glowRings.forEach((ring) => {
          (ring.material as THREE.MeshPhysicalMaterial).emissiveIntensity = emissiveProxies.layer3Intensity * 1.5;
        });
      },
    },
    3.0
  );

  mainTimeline.to(
    emissiveProxies,
    {
      layer3Intensity: 0,
      pointLightIntensity: 0,
      duration: 1.0,
      ease: "sine.inOut",
      onUpdate: () => {
        mainMesh3.material.emissive.copy(purpleEmissiveColor);
        mainMesh3.material.emissiveIntensity = emissiveProxies.layer3Intensity;
        accentPointLight.intensity = emissiveProxies.pointLightIntensity;

        glowRings.forEach((ring) => {
          (ring.material as THREE.MeshPhysicalMaterial).emissiveIntensity = emissiveProxies.layer3Intensity * 1.5;
        });
      },
    },
    4.0
  );

  // Particle drift trigger (3.2s to 4.8s)
  mainTimeline.add(() => {
    particleSystem.reset();
    particleSystem.timeline.play(0);
  }, 3.2);

  // --- Phase D: 5.0s – 7.2s: Smooth Reform & Re-alignment ---
  mainTimeline.to(
    layer1.position,
    { x: 0, y: base1Y, z: 0, duration: 2.2, ease: "power2.inOut" },
    5.0
  );
  mainTimeline.to(
    layer1.rotation,
    { x: 0, z: 0, duration: 2.2, ease: "power2.inOut" },
    5.0
  );

  mainTimeline.to(
    layer2.position,
    { x: 0, y: base2Y, z: 0, duration: 2.2, ease: "power2.inOut" },
    5.0
  );
  mainTimeline.to(
    layer2.rotation,
    { x: 0, z: 0, duration: 2.2, ease: "power2.inOut" },
    5.0
  );

  mainTimeline.to(
    layer3.position,
    { x: 0, y: base3Y, z: 0, duration: 2.2, ease: "power2.inOut" },
    5.0
  );

  mainTimeline.to(
    layer4.position,
    { x: 0, y: base4Y, z: 0, duration: 2.2, ease: "power2.inOut" },
    5.0
  );
  mainTimeline.to(
    layer4.rotation,
    { x: 0, z: 0, duration: 2.2, ease: "power2.inOut" },
    5.0
  );

  mainTimeline.to(
    layer5.position,
    { x: 0, y: base5Y, z: 0, duration: 2.2, ease: "power2.inOut" },
    5.0
  );
  mainTimeline.to(
    layer5.rotation,
    { x: 0, z: 0, duration: 2.2, ease: "power2.inOut" },
    5.0
  );

  // --- Phase E: 7.2s – 9.0s: Seamless Transition into Phase A Breathing State ---
  // Gently flows into the exact start position/velocity of t=0.0s (base1Y - 0.03 -> base1Y + 0.04)
  mainTimeline.to(
    layer1.position,
    { y: base1Y - 0.03, duration: 1.8, ease: "sine.inOut" },
    7.2
  );
  mainTimeline.to(
    layer2.position,
    { y: base2Y - 0.015, duration: 1.8, ease: "sine.inOut" },
    7.2
  );
  mainTimeline.to(
    layer3.position,
    { y: base3Y, duration: 1.8, ease: "sine.inOut" },
    7.2
  );
  mainTimeline.to(
    layer4.position,
    { y: base4Y + 0.015, duration: 1.8, ease: "sine.inOut" },
    7.2
  );
  mainTimeline.to(
    layer5.position,
    { y: base5Y + 0.03, duration: 1.8, ease: "sine.inOut" },
    7.2
  );

  const dispose = () => {
    backgroundSpin.kill();
    mainTimeline.kill();
  };

  return {
    mainTimeline,
    backgroundSpin,
    dispose,
  };
}
