"use client";

import Image from "next/image";
import Link from "next/link";

export default function Navbar() {
  return (
    <header className="relative z-20 w-full max-w-7xl mx-auto px-6 py-4 sm:py-5 flex items-center justify-between">
      {/* Left: Brand Logo */}
      <Link href="/" className="flex items-center gap-2 group cursor-pointer z-10">
        <Image
          src="/varve_clean.png"
          alt="Varve Logo"
          width={105}
          height={26}
          className="h-5 sm:h-6 w-auto object-contain transition-opacity group-hover:opacity-90"
          priority
        />
      </Link>

      {/* Center: Nav Links */}
      <nav className="hidden md:flex items-center gap-8 text-sm text-zinc-400 font-medium absolute left-1/2 -translate-x-1/2 z-10">
        <Link
          href="#features"
          className="hover:text-white transition-colors cursor-pointer"
        >
          Features
        </Link>
        <Link
          href="#docs"
          className="hover:text-white transition-colors cursor-pointer"
        >
          Docs
        </Link>
        <Link
          href="#ledger"
          className="hover:text-white transition-colors cursor-pointer"
        >
          Ledger
        </Link>
      </nav>

      {/* Right: Sleek Borderless Sign In Button */}
      <div className="flex items-center gap-4 z-10">
        <Link
          href="#sign-in"
          className="relative group inline-flex items-center justify-center px-4 py-2 rounded-xl text-xs font-semibold text-zinc-200 transition-all cursor-pointer select-none border border-white/15 bg-gradient-to-b from-zinc-800/90 via-zinc-900/90 to-zinc-950/95 backdrop-blur-xl shadow-[inset_0_1px_0_0_rgba(255,255,255,0.2),_0_4px_12px_-2px_rgba(0,0,0,0.6)] hover:border-white/25 hover:text-white hover:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.3),_0_6px_16px_-2px_rgba(0,0,0,0.8)] active:translate-y-[1px] active:shadow-inner"
        >
          Sign In
        </Link>
      </div>
    </header>
  );
}
