"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const pathname = usePathname();

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

      {/* Right: GitHub Icon & Skeuomorphic Sign In Button */}
      <div className="flex items-center gap-3 sm:gap-4 z-10">
        {/* GitHub Link Icon with Skeuomorphic Glass Styling */}
        <a
          href="https://github.com/cridiv/varve"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="GitHub Repository"
          className="relative group p-2.5 rounded-xl text-zinc-400 hover:text-white transition-all cursor-pointer select-none border border-white/10 bg-zinc-900/60 hover:bg-zinc-800/90 backdrop-blur-md shadow-sm active:translate-y-[1px]"
        >
          <svg
            className="w-5 h-5 fill-current"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            />
          </svg>
        </a>

        {/* Connect Button -> Redirects to /connect or shows Active state */}
        <Link
          href="/connect"
          className={`relative group inline-flex items-center justify-center px-4 py-2 rounded-xl text-xs font-semibold transition-all select-none border border-white/15 backdrop-blur-xl shadow-sm ${
            pathname === "/connect"
              ? "bg-[#9B7FF6]/20 border-[#9B7FF6]/50 text-[#9B7FF6] pointer-events-none"
              : "bg-gradient-to-b from-zinc-800/90 via-zinc-900/90 to-zinc-950/95 text-zinc-200 hover:border-white/25 hover:text-white hover:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.3),_0_6px_16px_-2px_rgba(0,0,0,0.8)] active:translate-y-[1px]"
          }`}
        >
          {pathname === "/connect" ? "Connecting" : "Connect"}
        </Link>
      </div>
    </header>
  );
}
