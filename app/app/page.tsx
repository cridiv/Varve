import Navbar from "@/components/Navbar";
import VarveHeroAnimation from "@/components/VarveHeroAnimation";
import LineageArchaeology from "@/components/LineageArchaeology";
import RiskTriageList from "@/components/RiskTriageList";
import LedgerVerification from "@/components/LedgerVerification";
import FAQ from "@/components/FAQ";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 font-sans selection:bg-[#9B7FF6] selection:text-white flex flex-col justify-between overflow-x-hidden">
      {/* Separated Navigation Header */}
      <Navbar />

      {/* Hero Section (Left Content, Right 3D Animation) */}
      <main className="relative w-full max-w-7xl mx-auto px-6 py-12 lg:py-20 my-auto">
        {/* Ambient Backlight Behind 3D Scene */}
        <div className="absolute top-1/2 -translate-y-1/2 right-[5%] w-[450px] h-[450px] bg-[#9B7FF6]/12 blur-[100px] rounded-full pointer-events-none z-0" />

        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-8 items-center">
          {/* Left Column: Simple Clean Hero Content */}
          <div className="flex flex-col items-start text-left space-y-6">
            {/* DataHub Tag */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider text-[#9B7FF6] uppercase border border-[#9B7FF6]/25 bg-gradient-to-b from-[#9B7FF6]/15 via-zinc-900/60 to-zinc-950/80 backdrop-blur-md shadow-[inset_0_1px_0_0_rgba(155,127,246,0.3),_0_2px_8px_-2px_rgba(0,0,0,0.5)]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#9B7FF6] animate-pulse" />
              <span>DataHub Native Lineage</span>
            </div>

            <h1 className="font-[family-name:var(--font-michroma)] text-3xl font-normal tracking-tight text-white sm:text-4xl lg:text-5xl leading-[1.25]">
              Tells you which production ML model will{" "}
              <span className="text-[#9B7FF6]">
                break next
              </span>
            </h1>

            <p className="text-base sm:text-lg text-zinc-400 leading-relaxed max-w-lg font-normal">
              Reads DataHub&apos;s lineage graph layer by layer to discover hidden technical debt before it becomes an incident.
            </p>

            {/* Realistic 3D Dark Glass Buttons */}
            <div className="pt-2 flex flex-wrap items-center gap-4">
              {/* Primary 3D Dark Glass Button */}
              <a
                href="#triage"
                className="relative group inline-flex items-center gap-2.5 px-7 py-3.5 rounded-xl font-semibold text-sm text-white transition-all cursor-pointer select-none border border-white/15 bg-gradient-to-b from-zinc-800/90 via-zinc-900/90 to-zinc-950/95 backdrop-blur-xl shadow-[inset_0_1px_0_0_rgba(255,255,255,0.2),_0_4px_20px_-2px_rgba(0,0,0,0.6),_0_0_15px_-3px_rgba(155,127,246,0.25)] hover:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.35),_0_6px_25px_-2px_rgba(0,0,0,0.8),_0_0_22px_-2px_rgba(155,127,246,0.4)] hover:border-white/25 active:translate-y-[1px] active:shadow-inner"
              >
                <span>Get Started</span>
                <span className="group-hover:translate-x-0.5 transition-transform text-[#9B7FF6]">
                  &rarr;
                </span>
              </a>

              {/* Secondary More Transparent 3D Glass Button */}
              <a
                href="#docs"
                className="relative group inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-medium text-sm text-zinc-300 transition-all cursor-pointer select-none border border-white/10 bg-gradient-to-b from-zinc-900/40 via-zinc-950/50 to-black/60 backdrop-blur-md shadow-[inset_0_1px_0_0_rgba(255,255,255,0.1),_0_4px_15px_-3px_rgba(0,0,0,0.5)] hover:bg-zinc-900/60 hover:text-white hover:border-white/15 active:translate-y-[1px]"
              >
                <span>Documentation</span>
              </a>
            </div>
          </div>

          {/* Right Column: 3D Sediment Core Hero Canvas */}
          <div className="relative w-full flex items-center justify-center">
            <VarveHeroAnimation className="w-full h-[500px] sm:h-[560px]" />
          </div>
        </div>
      </main>

      {/* Lineage Archaeology 4-Step Pipeline Component */}
      <LineageArchaeology />

      {/* Live Risk Triage List Component */}
      <RiskTriageList />

      {/* Interactive Hash-Chained Verification Ledger Component */}
      <LedgerVerification />

      {/* Frequently Asked Questions Component */}
      <FAQ />

      {/* Minimal Footer */}
      <footer className="relative z-10 w-full max-w-7xl mx-auto px-6 py-6 text-xs text-zinc-600 flex justify-between items-center border-t border-zinc-900">
        <div>&copy; {new Date().getFullYear()} Varve Inc.</div>
        <div className="text-zinc-500">Built with Three.js &amp; GSAP</div>
      </footer>
    </div>
  );
}
