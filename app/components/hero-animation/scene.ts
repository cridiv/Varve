import * as THREE from "three";

export interface SceneSetup {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  renderer: THREE.WebGLRenderer;
  keyLight: THREE.DirectionalLight;
  rimLight: THREE.DirectionalLight;
  accentRimLight: THREE.DirectionalLight;
  accentPointLight: THREE.PointLight;
  ambientLight: THREE.AmbientLight;
  shadowCatcher: THREE.Mesh;
  resize: (width: number, height: number) => void;
  dispose: () => void;
}

export function createScene(container: HTMLElement, width: number, height: number): SceneSetup {
  const scene = new THREE.Scene();
  scene.background = null;

  const camera = new THREE.PerspectiveCamera(28, width / height, 0.1, 100);
  camera.position.set(0, 0, 14);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  const maxPixelRatio = width < 768 ? 1.5 : 2;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, maxPixelRatio));
  renderer.setSize(width, height);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  container.appendChild(renderer.domElement);

  // Key light (Soft white studio key light)
  const keyLight = new THREE.DirectionalLight(0xffffff, 2.5);
  keyLight.position.set(-6, 8, 6);
  keyLight.castShadow = true;
  const shadowMapSize = width < 768 ? 1024 : 2048;
  keyLight.shadow.mapSize.width = shadowMapSize;
  keyLight.shadow.mapSize.height = shadowMapSize;
  keyLight.shadow.camera.near = 0.5;
  keyLight.shadow.camera.far = 25;
  keyLight.shadow.camera.left = -5;
  keyLight.shadow.camera.right = 5;
  keyLight.shadow.camera.top = 5;
  keyLight.shadow.camera.bottom = -5;
  keyLight.shadow.bias = -0.0003;
  scene.add(keyLight);

  // Blackish-gray Rim light (crisp neutral dark definition)
  const rimLight = new THREE.DirectionalLight(0x4a4b54, 1.6);
  rimLight.position.set(5, -3, -8);
  rimLight.castShadow = false;
  scene.add(rimLight);

  // Subtle Purple Accent Touch Light (#9B7FF6)
  const accentRimLight = new THREE.DirectionalLight(0x9b7ff6, 0.7);
  accentRimLight.position.set(-5, 4, -6);
  scene.add(accentRimLight);

  // Center Purple PointLight (Illuminates exploded gap from within)
  const accentPointLight = new THREE.PointLight(0x9b7ff6, 0, 8);
  accentPointLight.position.set(0, 0, 0);
  scene.add(accentPointLight);

  // Ambient light
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
  scene.add(ambientLight);

  // Ground shadow catcher
  const planeGeo = new THREE.PlaneGeometry(20, 20);
  const planeMat = new THREE.ShadowMaterial({ opacity: 0.4 });
  const shadowCatcher = new THREE.Mesh(planeGeo, planeMat);
  shadowCatcher.position.y = -1.8;
  shadowCatcher.rotation.x = -Math.PI / 2;
  shadowCatcher.receiveShadow = true;
  scene.add(shadowCatcher);

  const resize = (newWidth: number, newHeight: number) => {
    camera.aspect = newWidth / newHeight;
    camera.updateProjectionMatrix();
    const pixelRatioCap = newWidth < 768 ? 1.5 : 2;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, pixelRatioCap));
    renderer.setSize(newWidth, newHeight);
    const newShadowSize = newWidth < 768 ? 1024 : 2048;
    if (keyLight.shadow.mapSize.width !== newShadowSize) {
      keyLight.shadow.mapSize.width = newShadowSize;
      keyLight.shadow.mapSize.height = newShadowSize;
      keyLight.shadow.map?.dispose();
      keyLight.shadow.map = null;
    }
  };

  const dispose = () => {
    renderer.dispose();
    planeGeo.dispose();
    planeMat.dispose();
    if (renderer.domElement && renderer.domElement.parentElement) {
      renderer.domElement.parentElement.removeChild(renderer.domElement);
    }
  };

  return {
    scene,
    camera,
    renderer,
    keyLight,
    rimLight,
    accentRimLight,
    accentPointLight,
    ambientLight,
    shadowCatcher,
    resize,
    dispose,
  };
}
