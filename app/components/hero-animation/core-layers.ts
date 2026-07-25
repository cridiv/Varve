import * as THREE from "three";

export interface LayerConfig {
  name: string;
  assembledY: number;
  color: string;
  roughness: number;
  metalness: number;
  clearcoat: number;
  emissive?: string;
}

export const LAYER_CONFIGS: LayerConfig[] = [
  {
    name: "layer-1",
    assembledY: 1.16,
    color: "#2C2D30",
    roughness: 0.32,
    metalness: 0.45,
    clearcoat: 1.0,
  },
  {
    name: "layer-2",
    assembledY: 0.58,
    color: "#212225",
    roughness: 0.35,
    metalness: 0.4,
    clearcoat: 1.0,
  },
  {
    name: "layer-3",
    assembledY: 0,
    color: "#18191C",
    roughness: 0.28,
    metalness: 0.5,
    clearcoat: 1.0,
    emissive: "#9B7FF6",
  },
  {
    name: "layer-4",
    assembledY: -0.58,
    color: "#111214",
    roughness: 0.35,
    metalness: 0.4,
    clearcoat: 1.0,
  },
  {
    name: "layer-5",
    assembledY: -1.16,
    color: "#0A0B0C",
    roughness: 0.38,
    metalness: 0.4,
    clearcoat: 1.0,
  },
];

export interface CoreLayers {
  coreGroup: THREE.Group;
  layers: Map<string, THREE.Group>;
  mainMeshes: Map<string, THREE.Mesh<THREE.CylinderGeometry, THREE.MeshPhysicalMaterial>>;
  glowRings: THREE.Mesh[];
  dispose: () => void;
}

export function createCoreLayers(): CoreLayers {
  const coreGroup = new THREE.Group();
  coreGroup.name = "coreGroup";

  const layers = new Map<string, THREE.Group>();
  const mainMeshes = new Map<string, THREE.Mesh<THREE.CylinderGeometry, THREE.MeshPhysicalMaterial>>();
  const glowRings: THREE.Mesh[] = [];

  const geometriesToDispose: THREE.BufferGeometry[] = [];
  const materialsToDispose: THREE.Material[] = [];

  const radius = 1.95;
  const height = 0.58;
  const radialSegments = 64;

  LAYER_CONFIGS.forEach((config) => {
    // Parent group for this individual layer
    const layerGroup = new THREE.Group();
    layerGroup.name = config.name;
    layerGroup.position.set(0, config.assembledY, 0);

    // 1. Main Cylinder Mesh
    const cylinderGeo = new THREE.CylinderGeometry(radius, radius, height, radialSegments, 1);
    geometriesToDispose.push(cylinderGeo);

    const mainMat = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color(config.color),
      roughness: config.roughness,
      metalness: config.metalness,
      clearcoat: config.clearcoat,
      clearcoatRoughness: 0.08,
      reflectivity: 0.9,
      emissive: config.emissive ? new THREE.Color(config.emissive) : new THREE.Color(0x000000),
      emissiveIntensity: 0,
    });
    materialsToDispose.push(mainMat);

    const mainMesh = new THREE.Mesh(cylinderGeo, mainMat);
    mainMesh.castShadow = true;
    mainMesh.receiveShadow = true;
    layerGroup.add(mainMesh);
    mainMeshes.set(config.name, mainMesh);

    // 2. Beveled Top & Bottom Rim Rings for crisp metallic highlights (Resend style)
    const rimGeo = new THREE.TorusGeometry(radius - 0.02, 0.025, 16, radialSegments);
    geometriesToDispose.push(rimGeo);

    const rimMat = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color(config.color).clone().multiplyScalar(1.3), // slightly brighter highlight edge
      roughness: 0.2,
      metalness: 0.7,
      clearcoat: 1.0,
      clearcoatRoughness: 0.05,
    });
    materialsToDispose.push(rimMat);

    const topRim = new THREE.Mesh(rimGeo, rimMat);
    topRim.position.y = height / 2;
    topRim.rotation.x = Math.PI / 2;
    topRim.castShadow = true;
    layerGroup.add(topRim);

    const bottomRim = new THREE.Mesh(rimGeo, rimMat);
    bottomRim.position.y = -height / 2;
    bottomRim.rotation.x = Math.PI / 2;
    bottomRim.castShadow = true;
    layerGroup.add(bottomRim);

    // 3. Inset Technical Grooves / Lineage Details (Resend 3D micro-details)
    const grooveGeo = new THREE.TorusGeometry(radius + 0.005, 0.012, 8, radialSegments);
    geometriesToDispose.push(grooveGeo);

    const grooveMat = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color("#111115"),
      roughness: 0.1,
      metalness: 0.9,
      clearcoat: 1.0,
    });
    materialsToDispose.push(grooveMat);

    const midGroove = new THREE.Mesh(grooveGeo, grooveMat);
    midGroove.rotation.x = Math.PI / 2;
    layerGroup.add(midGroove);

    // 4. Special Core Glowing Ring for Layer 3 (Center Layer)
    if (config.name === "layer-3") {
      const glowRingGeo = new THREE.TorusGeometry(radius * 0.85, 0.04, 16, 64);
      geometriesToDispose.push(glowRingGeo);

      const glowRingMat = new THREE.MeshPhysicalMaterial({
        color: new THREE.Color("#9B7FF6"),
        emissive: new THREE.Color("#9B7FF6"),
        emissiveIntensity: 0,
        roughness: 0.1,
        metalness: 0.1,
        transparent: true,
        opacity: 0.9,
      });
      materialsToDispose.push(glowRingMat);

      const glowRing = new THREE.Mesh(glowRingGeo, glowRingMat);
      glowRing.rotation.x = Math.PI / 2;
      layerGroup.add(glowRing);
      glowRings.push(glowRing);
    }

    coreGroup.add(layerGroup);
    layers.set(config.name, layerGroup);
  });

  const dispose = () => {
    geometriesToDispose.forEach((g) => g.dispose());
    materialsToDispose.forEach((m) => m.dispose());
  };

  return {
    coreGroup,
    layers,
    mainMeshes,
    glowRings,
    dispose,
  };
}
