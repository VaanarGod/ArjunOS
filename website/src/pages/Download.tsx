import Section from '../components/ui/Section'
import MagneticButton from '../components/ui/MagneticButton'
import { Download, Github, Apple, Terminal, AlertTriangle, CheckCircle2, ExternalLink, ChevronDown } from 'lucide-react'
import { APP_VERSION, MIN_MACOS, LICENSE, RELEASES_URL, DOWNLOAD_URL } from '../data/content'

export default function DownloadPage() {
  return (
    <>
      <Section className="min-h-[80vh] flex flex-col justify-center">
        <div className="mx-auto max-w-3xl text-center">
          
          <div className="mx-auto mb-8 flex h-20 w-20 items-center justify-center rounded-3xl border border-cyan/30 bg-cyan/10 shadow-[0_0_50px_rgba(34,211,238,0.3)] animate-pulse-slow">
            <div className="h-10 w-10 rounded-full bg-cyan shadow-[0_0_20px_rgba(34,211,238,0.8)]" />
          </div>
          
          <h1 className="font-display text-5xl font-semibold tracking-tight text-white sm:text-6xl mb-6">
            Ready to launch.
          </h1>
          
          <p className="text-lg text-gray-400 mb-8 max-w-xl mx-auto leading-relaxed">
            ArjunOS <span className="font-mono text-cyan/80">v{APP_VERSION}</span>{' '}
            is officially available for macOS. Download the disk image below to start running your local AI models.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 mb-10">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan/20 bg-cyan/5 px-3 py-1 text-xs text-cyan">
              <CheckCircle2 size={13} /> Latest Release v{APP_VERSION}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-gray-300">
              <Apple size={13} /> {MIN_MACOS}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-gray-300">
              {LICENSE}
            </span>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <MagneticButton 
              href={DOWNLOAD_URL} 
              className="w-full sm:w-auto bg-cyan text-void shadow-glow-strong hover:bg-ice text-lg px-10 py-4"
            >
              <Download size={20} /> Download .dmg
            </MagneticButton>
            <MagneticButton 
              href={RELEASES_URL} 
              className="w-full sm:w-auto border border-white/10 bg-white/5 text-white hover:border-cyan/30 hover:bg-cyan/10 px-8 py-4"
            >
              <Github size={18} /> Release Notes
            </MagneticButton>
          </div>

          <p className="mt-8 text-xs text-gray-500 max-w-lg mx-auto">
            Ad-hoc signed for local use, not notarized. If macOS blocks it on another Mac, right-click the app → Open. 
            <br className="mt-2" />
            Direct link: <a href={DOWNLOAD_URL} className="text-cyan/70 hover:text-cyan font-mono">ArjunOS-{APP_VERSION}.dmg <ExternalLink size={10} className="inline" /></a>
          </p>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="grid gap-6 md:grid-cols-2 max-w-4xl mx-auto">
          <div className="glass rounded-2xl p-6 border border-white/5 bg-[#050505]/80">
            <Terminal className="mb-4 h-6 w-6 text-cyan" />
            <h2 className="font-display text-lg font-semibold text-white mb-2">Where your data lives</h2>
            <ul className="space-y-1.5 text-sm text-gray-400">
              <li>State: <span className="font-mono text-gray-300">~/Library/Application Support/JarvisOS/state</span></li>
              <li>Conversations: <span className="font-mono text-gray-300">…/JarvisOS/conversations</span></li>
              <li>Workspace: <span className="font-mono text-gray-300">…/state/workspace</span></li>
            </ul>
          </div>

          <div className="glass rounded-2xl p-6 border border-white/5 bg-[#050505]/80">
            <AlertTriangle className="mb-4 h-6 w-6 text-yellow-500" />
            <h2 className="font-display text-lg font-semibold text-white mb-2">Requirements</h2>
            <ul className="space-y-1.5 text-sm text-gray-400">
              <li>{MIN_MACOS}</li>
              <li>A local model server (e.g., Ollama, LM Studio)</li>
              <li>Python 3.11+ (bundled in the .app)</li>
            </ul>
          </div>
        </div>
      </Section>

      {/* Developer Section - Collapsible */}
      <Section className="pt-0 pb-32">
        <details className="group max-w-4xl mx-auto rounded-2xl border border-white/5 bg-[#050505]/50 overflow-hidden">
          <summary className="flex items-center justify-between p-6 cursor-pointer hover:bg-white/[0.02] transition-colors list-none">
            <div className="flex items-center gap-3">
              <Terminal size={18} className="text-gray-400 group-open:text-cyan" />
              <span className="font-medium text-gray-300 group-open:text-white">Build from source (Developers)</span>
            </div>
            <ChevronDown size={18} className="text-gray-500 group-open:rotate-180 transition-transform" />
          </summary>
          <div className="p-6 pt-0 border-t border-white/5">
            <p className="text-sm text-gray-400 mb-4 mt-4">
              If you prefer to inspect the code or build the app yourself:
            </p>
            <pre className="overflow-x-auto rounded-xl border border-cyan/10 bg-[#000000] p-5 text-[12px] leading-relaxed text-cyan/80">
{`# 1. Clone the repository
git clone https://github.com/VaanarGod/ArjunOS.git
cd ArjunOS

# 2. Setup environment
scripts/doctor.sh        # read-only report
scripts/setup.sh         # bridge virtualenv

# 3. Run the app
cd apps/macos && swift run JarvisOS

# 4. Package to .dmg
cd ../..
scripts/package.sh`}
            </pre>
          </div>
        </details>
      </Section>
    </>
  )
}
