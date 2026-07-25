import { createScene, SceneSetup } from "./scene";
import { createCoreLayers, CoreLayers } from "./core-layers";
import { createParticleSystem, ParticleSystem } from "./particles";
import { createAnimationTimeline, AnimationTimeline } from "./timeline";

export interface HeroAnimationController {
  dispose: () => void;
}

export function initHeroAnimation(container: HTMLElement): HeroAnimationController {
  const width = container.clientWidth || 600;
  const height = container.clientHeight || 500;

  // Check prefers-reduced-motion
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 1. Create Scene, Camera, Studio Lights & Renderer
  const sceneSetup: SceneSetup = createScene(container, width, height);
  const { scene, camera, renderer, resize, dispose: disposeScene } = sceneSetup;

  // 2. Create 5 Layers Mesh Group (Resend 3D Style)
  const coreLayers: CoreLayers = createCoreLayers();
  const { coreGroup, layers, dispose: disposeLayers } = coreLayers;
  scene.add(coreGroup);

  // 3. Create Glowing Particle System
  const particleSystem: ParticleSystem = createParticleSystem();
  coreGroup.add(particleSystem.points);

  let animTimeline: AnimationTimeline | null = null;
  let animFrameId: number | null = null;
  let isIntersecting = true;

  // Mouse Parallax
  let targetCamX = 0;
  let targetCamY = 0;

  const handleMouseMove = (event: MouseEvent) => {
    const rect = container.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
    targetCamX = x * 0.2;
    targetCamY = y * 0.2;
  };

  window.addEventListener("mousemove", handleMouseMove);

  // Render loop
  const renderLoop = () => {
    if (isIntersecting) {
      // Lerp camera parallax
      camera.position.x += (targetCamX - camera.position.x) * 0.025;
      camera.position.y += (targetCamY - camera.position.y) * 0.025;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);
      animFrameId = requestAnimationFrame(renderLoop);
    }
  };

  if (prefersReducedMotion) {
    // Reduced motion mode: Static held-apart (3.2s) state without GSAP loop
    const layer1 = layers.get("layer-1");
    const layer2 = layers.get("layer-2");
    const layer4 = layers.get("layer-4");
    const layer5 = layers.get("layer-5");

    if (layer1) {
      layer1.position.set(-1.4, 2.6, 0.4);
      layer1.rotation.z = 0.15;
    }
    if (layer2) {
      layer2.position.set(1.3, 1.5, -0.3);
      layer2.rotation.z = -0.1;
    }
    if (layer4) {
      layer4.position.set(-1.3, -1.5, -0.3);
      layer4.rotation.z = 0.1;
    }
    if (layer5) {
      layer5.position.set(1.4, -2.6, 0.4);
      layer5.rotation.z = -0.15;
    }

    renderer.render(scene, camera);
  } else {
    // Standard full GSAP Timeline Loop
    animTimeline = createAnimationTimeline(coreLayers, particleSystem, sceneSetup);
    renderLoop();
  }

  // Handle Resize
  const handleResize = () => {
    const newWidth = container.clientWidth || 600;
    const newHeight = container.clientHeight || 500;
    resize(newWidth, newHeight);
    if (prefersReducedMotion) {
      renderer.render(scene, camera);
    }
  };

  window.addEventListener("resize", handleResize);

  // IntersectionObserver to pause loop off-screen
  const observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0];
      isIntersecting = entry.isIntersecting;
      if (isIntersecting && !prefersReducedMotion) {
        if (!animFrameId) {
          animFrameId = requestAnimationFrame(renderLoop);
        }
      } else {
        if (animFrameId) {
          cancelAnimationFrame(animFrameId);
          animFrameId = null;
        }
      }
    },
    { threshold: 0.1 }
  );

  observer.observe(container);

  const dispose = () => {
    window.removeEventListener("resize", handleResize);
    window.removeEventListener("mousemove", handleMouseMove);
    observer.disconnect();
    if (animFrameId) {
      cancelAnimationFrame(animFrameId);
    }
    if (animTimeline) {
      animTimeline.dispose();
    }
    particleSystem.dispose();
    disposeLayers();
    disposeScene();
  };

  return { dispose };
}
