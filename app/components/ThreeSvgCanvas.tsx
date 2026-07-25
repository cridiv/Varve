"use client";

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { SVGRenderer } from "three/examples/jsm/renderers/SVGRenderer.js";
import gsap from "gsap";

interface ThreeSvgCanvasProps {
  width?: number;
  height?: number;
  className?: string;
}

export default function ThreeSvgCanvas({
  width = 600,
  height = 500,
  className = "",
}: ThreeSvgCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgString, setSvgString] = useState<string>("");

  useEffect(() => {
    if (!containerRef.current) return;

    // 1. Setup Three.js Scene, Camera, & SVGRenderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 8);

    const renderer = new SVGRenderer();
    renderer.setSize(width, height);
    
    // Clear existing children
    const container = containerRef.current;
    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // 2. Create 3D Geometric Meshes for Vector SVG Rendering
    const group = new THREE.Group();
    scene.add(group);

    // Core Icosahedron (Wireframe / Edge vectors look crisp in SVG)
    const geoMain = new THREE.IcosahedronGeometry(1.8, 1);
    const matMain = new THREE.MeshBasicMaterial({
      color: 0x4f46e5, // Indigo
      wireframe: true,
      wireframeLinewidth: 2,
    });
    const meshMain = new THREE.Mesh(geoMain, matMain);
    group.add(meshMain);

    // Outer Ring
    const geoRing = new THREE.TorusGeometry(2.8, 0.05, 16, 100);
    const matRing = new THREE.MeshBasicMaterial({
      color: 0x06b6d4, // Cyan
      wireframe: true,
    });
    const meshRing = new THREE.Mesh(geoRing, matRing);
    meshRing.rotation.x = Math.PI / 3;
    group.add(meshRing);

    // Floating Orbit Nodes
    const nodesGroup = new THREE.Group();
    const nodeGeo = new THREE.OctahedronGeometry(0.25);
    const nodeMat = new THREE.MeshBasicMaterial({
      color: 0xf59e0b, // Amber
      wireframe: false,
    });

    const nodeCount = 5;
    for (let i = 0; i < nodeCount; i++) {
      const angle = (i / nodeCount) * Math.PI * 2;
      const radius = 3.2;
      const node = new THREE.Mesh(nodeGeo, nodeMat);
      node.position.set(
        Math.cos(angle) * radius,
        Math.sin(angle) * radius * 0.4,
        Math.sin(angle) * radius
      );
      nodesGroup.add(node);
    }
    group.add(nodesGroup);

    // 3. Render function
    const renderScene = () => {
      renderer.render(scene, camera);
    };

    // Initial render
    renderScene();

    // 4. GSAP Passive Timeline Loop (No ScrollTrigger)
    const tl = gsap.timeline({
      repeat: -1,
      yoyo: true,
      onUpdate: renderScene,
    });

    // Sequence 1: Smooth 3D Group Rotation
    tl.to(group.rotation, {
      y: Math.PI * 2,
      x: Math.PI * 0.5,
      duration: 8,
      ease: "power1.inOut",
    });

    // Sequence 2: Pulsing Scale and Orbit rotation
    tl.to(
      meshMain.scale,
      {
        x: 1.25,
        y: 1.25,
        z: 1.25,
        duration: 4,
        ease: "sine.inOut",
      },
      0
    );

    tl.to(
      nodesGroup.rotation,
      {
        z: -Math.PI * 2,
        duration: 8,
        ease: "none",
      },
      0
    );

    // Helper to capture exported SVG code
    const captureSvg = () => {
      if (renderer.domElement) {
        setSvgString(renderer.domElement.outerHTML);
      }
    };

    captureSvg();

    // Cleanup on unmount
    return () => {
      tl.kill();
      renderer.domElement.remove();
    };
  }, [width, height]);

  const handleDownloadSvg = () => {
    if (!containerRef.current) return;
    const svgElement = containerRef.current.querySelector("svg");
    if (!svgElement) return;

    const svgData = new XMLSerializer().serializeToString(svgElement);
    const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "3d-scene.svg";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`flex flex-col items-center gap-4 ${className}`}>
      <div
        ref={containerRef}
        className="relative border border-zinc-200 dark:border-zinc-800 rounded-xl bg-gradient-to-b from-zinc-50 to-zinc-100 dark:from-zinc-950 dark:to-zinc-900 shadow-xl overflow-hidden p-4"
        style={{ width: `${width}px`, height: `${height}px` }}
      />
      <div className="flex gap-3">
        <button
          onClick={handleDownloadSvg}
          className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow transition-colors flex items-center gap-2 cursor-pointer"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          Export 3D SVG
        </button>
      </div>
    </div>
  );
}
