import VarveHeroAnimation from "@/components/VarveHeroAnimation";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 font-sans selection:bg-[#9B7FF6] selection:text-white flex flex-col justify-between overflow-x-hidden">
      {/* Navigation Header */}
      <nav className="relative z-10 w-full max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold text-xl tracking-tight">
          <span className="w-3 h-3 rounded-full bg-[#9B7FF6] shadow-[0_0_12px_#9B7FF6]" />
          <span>Varve</span>
        </div>
        <div className="flex items-center gap-6 text-sm text-zinc-400">
          <a href="#features" className="hover:text-white transition-colors">
            Features
          </a>
          <a href="#docs" className="hover:text-white transition-colors">
            Docs
          </a>
          <a
            href="#get-started"
            className="px-4 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-white font-medium hover:bg-zinc-800 transition-colors"
          >
            Sign In
          </a>
        </div>
      </nav>

      {/* Hero Section (Left Content, Right 3D Animation) */}
      <main className="relative w-full max-w-7xl mx-auto px-6 py-12 lg:py-20 my-auto">
        {/* Ambient Backlight Behind 3D Scene */}
        <div className="absolute top-1/2 -translate-y-1/2 right-[5%] w-[450px] h-[450px] bg-[#9B7FF6]/12 blur-[100px] rounded-full pointer-events-none z-0" />



        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-8 items-center">
          {/* Left Column: Content & Hero Buttons */}
          <div className="flex flex-col items-start text-left space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold tracking-wider text-[#9B7FF6] bg-[#9B7FF6]/10 border border-[#9B7FF6]/30 rounded-full uppercase shadow-inner backdrop-blur-md">
              <span className="w-2 h-2 rounded-full bg-[#9B7FF6] animate-pulse" />
              ML Lineage Archaeology
            </div>

            <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-6xl leading-[1.1]">
              Tells you which production ML model will{" "}
              <span className="bg-gradient-to-r from-zinc-100 via-zinc-300 to-[#9B7FF6] bg-clip-text text-transparent">
                break next
              </span>
            </h1>

            <p className="text-base sm:text-lg text-zinc-400 leading-relaxed max-w-xl">
              Varve reads DataHub&apos;s lineage graph layer by layer to discover hidden technical debt before it becomes an incident.
            </p>

            {/* CTAs */}
            <div className="pt-2 flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
              <a
                href="#triage"
                className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-white text-zinc-950 font-semibold text-sm hover:bg-zinc-200 transition-all shadow-lg hover:shadow-[#9B7FF6]/20 cursor-pointer text-center"
              >
                Start Free Triage
              </a>
              <a
                href="#demo"
                className="w-full sm:w-auto px-7 py-3.5 rounded-xl border border-zinc-800 bg-zinc-900/80 text-zinc-300 font-semibold text-sm hover:bg-zinc-800 hover:text-white transition-all cursor-pointer text-center"
              >
                View Verification Ledger
              </a>
            </div>
          </div>

          {/* Right Column: 3D Sediment Core Hero Canvas */}
          <div className="relative w-full flex items-center justify-center">
            <VarveHeroAnimation className="w-full h-[500px] sm:h-[560px]" />
          </div>
        </div>
      </main>

      {/* Minimal Footer */}
      <footer className="relative z-10 w-full max-w-7xl mx-auto px-6 py-6 text-xs text-zinc-600 flex justify-between items-center border-t border-zinc-900">
        <div>&copy; {new Date().getFullYear()} Varve Inc.</div>
        <div className="text-zinc-500">Built with Three.js &amp; GSAP</div>
      </footer>
    </div>
  );
}
