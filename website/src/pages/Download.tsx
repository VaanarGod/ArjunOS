import Section from '../components/ui/Section'
import MagneticButton from '../components/ui/MagneticButton'
import { Download, Github, Apple, Terminal, AlertTriangle, CheckCircle2, ExternalLink } from 'lucide-react'
import { APP_VERSION, APP_STATUS, MIN_MACOS, LICENSE, REPO_URL, RELEASES_URL, DOWNLOAD_URL } from '../data/content'

export default function DownloadPage() {
  return (
    <>
      <Section>
        <div className="mx-auto max-w-3xl text-center">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan/30 bg-cyan/10">
            <div className="h-7 w-7 rounded-full bg-cyan shadow-[0_0_30px_rgba(34,211,238,0.8)]" />
          </div>
          <h1 className="font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            Download ArjunOS
          </h1>
          <p className="mt-5 text-gray-400">
            ArjunOS <span className="font-mono text-cyan/80">v{APP_VERSION}</span>{' '}
            is ready. Download the latest macOS release below, or build it
            from source if you prefer.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
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

          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <MagneticButton href={DOWNLOAD_URL} className="bg-cyan text-void shadow-glow-strong hover:bg-ice">
              <Download size={16} /> Download ArjunOS v{APP_VERSION}
            </MagneticButton>
            <MagneticButton href={RELEASES_URL} className="border border-white/10 bg-white/5 text-white hover:border-cyan/30">
              <Github size={16} /> View all releases
            </MagneticButton>
          </div>

          <p className="mt-6 text-xs text-gray-500">
            Direct download:{' '}
            <a href={DOWNLOAD_URL} className="inline-flex items-center gap-1 font-mono text-cyan/70 hover:text-cyan">
              ArjunOS-{APP_VERSION}.dmg <ExternalLink size={11} />
            </a>
            <br className="mt-1" />
            Ad-hoc signed for local use, not notarized. If macOS blocks it on another Mac, right-click → Open.
          </p>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="grid gap-6 md:grid-cols-3">
          <div className="glass rounded-2xl p-6">
            <Apple className="mb-4 h-6 w-6 text-cyan" />
            <h2 className="font-display text-lg font-semibold text-white">Compatibility</h2>
            <ul className="mt-2 space-y-1.5 text-sm text-gray-400">
              <li>{MIN_MACOS}</li>
              <li>Xcode 15+ or Swift 5.9 toolchain</li>
              <li>Python 3.11+</li>
              <li>Optional: Ollama or another local model server</li>
            </ul>
          </div>
          <div className="glass rounded-2xl p-6">
            <Download className="mb-4 h-6 w-6 text-cyan" />
            <h2 className="font-display text-lg font-semibold text-white">Current version</h2>
            <p className="mt-2 font-mono text-sm text-cyan/80">v{APP_VERSION}</p>
            <p className="mt-2 text-sm text-gray-400">
              Early build. The chat core, safety layer, memory, MCP, web search, file reading and the interface are real and have been run on a Mac.
            </p>
          </div>
          <div className="glass rounded-2xl p-6">
            <Github className="mb-4 h-6 w-6 text-cyan" />
            <h2 className="font-display text-lg font-semibold text-white">GitHub Releases</h2>
            <p className="mt-2 text-sm text-gray-400">
              The canonical release channel. All assets and source code are available there.
            </p>
            <a href={RELEASES_URL} target="_blank" rel="noreferrer" className="mt-4 inline-block text-xs font-medium text-cyan hover:text-ice">
              Open releases →
            </a>
          </div>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="rounded-3xl border border-white/5 bg-white/[0.02] p-6 md:p-10">
          <div className="mb-5 flex items-center gap-2">
            <Terminal className="h-5 w-5 text-cyan" />
            <h2 className="font-display text-xl font-semibold text-white">Build from source</h2>
          </div>
          <p className="text-sm text-gray-400">
            If you prefer to inspect the code or modify the application:
          </p>
          <pre className="mt-4 overflow-x-auto rounded-2xl border border-cyan/10 bg-void/70 p-4 text-[12px] leading-relaxed text-cyan/80">
{`# 1. Clone
git clone ${REPO_URL}
cd ArjunOS

# 2. Environment
scripts/doctor.sh        # read-only environment report
scripts/setup.sh         # creates the bridge virtualenv and installs it
cd apps/macos && swift run JarvisOS

# 3. Install a model yourself (ArjunOS never downloads weights)
ollama pull llama3.2:3b

# 4. Package a .app and .dmg
cd ../..
scripts/package.sh              # dist/ArjunOS.app and dist/ArjunOS-${APP_VERSION}.dmg
scripts/package.sh --open       # ...and launch it
scripts/package.sh --install    # ...and copy to ~/Applications`}
          </pre>

          <div className="mt-6 flex items-start gap-3 rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-4 text-sm text-yellow-200/90">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <p>
              Prefer the packaged <span className="font-mono">.app</span> over{' '}
              <span className="font-mono">swift run</span>: a bare executable is
              not a real app bundle, which can make keyboard input unreliable.
              If the bridge fails to start, the app stays usable and shows the
              reason in <strong>Settings → Diagnostics → Restart</strong>.
            </p>
          </div>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
          <h2 className="font-display text-lg font-semibold text-white">Where your data lives</h2>
          <ul className="mt-3 space-y-1.5 text-sm text-gray-400">
            <li>State (memory, profile, audit): <span className="font-mono text-gray-300">~/Library/Application Support/JarvisOS/state</span></li>
            <li>Conversations: <span className="font-mono text-gray-300">~/Library/Application Support/JarvisOS/conversations/*.json</span></li>
            <li>Workspace: <span className="font-mono text-gray-300">…/state/workspace</span></li>
            <li>Bridge virtualenv: <span className="font-mono text-gray-300">~/Library/Application Support/JarvisOS/venv</span></li>
          </ul>
          <p className="mt-3 text-xs text-gray-500">Back up by copying that folder. Uninstall by deleting it.</p>
        </div>
      </Section>
    </>
  )
}
