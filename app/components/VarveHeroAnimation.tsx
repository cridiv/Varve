"use client";

import React, { useEffect, useRef } from "react";
import { initHeroAnimation, HeroAnimationController } from "./hero-animation";

interface VarveHeroAnimationProps {
  className?: string;
  width?: string;
  height?: string;
}

export default function VarveHeroAnimation({
  className = "",
  width = "100%",
  height = "520px",
}: VarveHeroAnimationProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const controller: HeroAnimationController = initHeroAnimation(containerRef.current);

    return () => {
      controller.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden flex items-center justify-center ${className}`}
      style={{ width, height }}
    />
  );
}
