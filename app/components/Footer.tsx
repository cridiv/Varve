"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";

export default function Footer() {
  return (
    <footer className="relative z-10 w-full bg-[#09090b] overflow-hidden">
      {/* Skeuomorphic Glass Top Border Line with Specular Light Bevel */}
      <div className="relative w-full h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent shadow-[0_1px_0_0_rgba(0,0,0,0.8),_0_-1px_0_0_rgba(255,255,255,0.15)]">
        {/* Soft Center Backlight Glow strictly scoped inside footer container below border line */}
        <div className="absolute left-1/2 -translate-x-1/2 top-0 w-[350px] sm:w-[450px] h-[70px] bg-[#9B7FF6]/20 blur-[50px] rounded-full pointer-events-none" />
      </div>

      <div className="max-w-7xl mx-auto px-6 py-12 lg:py-16 relative">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-10 items-start">
          {/* Column 1: Logo & Tagline (5 cols) */}
          <div className="md:col-span-5 space-y-4">
            <Link href="/" className="inline-block group cursor-pointer">
              <Image
                src="/varve_clean.png"
                alt="Varve Logo"
                width={105}
                height={26}
                className="h-6 w-auto object-contain transition-opacity group-hover:opacity-90"
              />
            </Link>
            <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed max-w-sm font-normal">
              ML Lineage Archaeology — composition of DataHub primitives to prove where your next production outage will originate.
            </p>
          </div>

          {/* Column 2: Navigation Links (3 cols) */}
          <div className="md:col-span-3 space-y-3">
            <div className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Platform
            </div>
            <ul className="space-y-2 text-xs text-zinc-400 font-medium">
              <li>
                <Link href="#features" className="hover:text-white transition-colors cursor-pointer">
                  Archaeology Pipeline
                </Link>
              </li>
              <li>
                <Link href="#triage" className="hover:text-white transition-colors cursor-pointer">
                  Live Risk Triage
                </Link>
              </li>
              <li>
                <Link href="#ledger" className="hover:text-white transition-colors cursor-pointer">
                  Verification Ledger
                </Link>
              </li>
              <li>
                <Link href="#faq" className="hover:text-white transition-colors cursor-pointer">
                  Documentation &amp; FAQ
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3: DataHub Ecosystem & Tech (4 cols) */}
          <div className="md:col-span-4 space-y-3">
            <div className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Architecture &amp; Engine
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Built natively for <strong className="text-zinc-200">DataHub metadata graphs</strong>. 3D WebGL engine rendered with <strong className="text-zinc-200">Three.js</strong> and <strong className="text-zinc-200">GSAP</strong>.
            </p>
            <div className="pt-2 flex items-center gap-3 text-[11px] text-zinc-500 font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>All Systems Operational</span>
            </div>
          </div>
        </div>

        {/* Bottom Skeuomorphic Separator Line */}
        <div className="mt-12 pt-6 border-t border-white/10 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-500">
          <div>
            &copy; {new Date().getFullYear()} Varve Inc. All rights reserved.
          </div>

          <div className="flex items-center gap-6">
            <span className="hover:text-zinc-400 transition-colors cursor-pointer">Privacy</span>
            <span className="hover:text-zinc-400 transition-colors cursor-pointer">Terms</span>
            <span className="hover:text-zinc-400 transition-colors cursor-pointer">Security</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
