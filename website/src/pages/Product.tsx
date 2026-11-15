import Section from '../components/ui/Section'
import Scene3D from '../components/three/Scene3D'
import Screenshot from '../components/ui/Screenshot'
import { screenshots } from '../data/content'
import { Monitor, ArrowRight, Layers, Shield, HardDrive } from 'lucide-react'

const architecture = `┌──────────────────────────── macOS ────────────────────────────┐
│  ArjunOS.app  (SwiftUI)                                        │
│   UI · conversations (JSON files) · Keychain wrapper           │
│        │  http://127.0.0.1:<random port>   (loopback only)     │
│        │  Authorization: Bearer <random per-launch token>      │
│        ▼                                                       │
│  jarvis_bridge  (Python, FastAPI)                              │
│   discovery → providers → orchestrator → tools                 │
│   memory · MCP · crew · files · settings · audit               │
│        ▼                    ▼                    ▼             │
│  Ollama / OpenAI-    MCP servers          DuckDuckGo           │
│  compatible (local)  (stdio or HTTPS)     (queries only)       │
└────────────────────────────────────────────────────────────────┘`

export default function Product() {
  return (
    <>
      <div className="fixed inset-0 z-0"><Scene3D variant="blueprint" /></div>
      <div className="pointer-events-none fixed inset-0 bg-glass-panels z-0" />
      <div className="relative z-10">
      <Section>
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan">Product</p>
          <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            A closer look at the macOS application.
          </h1>
          <p className="mt-5 text-gray-400">
            ArjunOS is a separate macOS application. This page shows the actual
            interface areas. Screenshots render from{' '}
            <span className="font-mono text-cyan/80">public/images/</span>. Drop
            real captures in with the filenames below and they appear here
            automatically.
          </p>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="grid gap-8">
          {screenshots.map((shot) => (
            <div key={shot.file} className="grid items-center gap-8 rounded-3xl border border-white/5 bg-white/[0.02] p-6 md:grid-cols-2 md:p-10">
              <div>
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan/20 bg-cyan/5 px-3 py-1 text-[11px] text-cyan">
                  <Monitor size={13} />
                  macOS
                </div>
                <h2 className="font-display text-2xl font-semibold text-white">{shot.title}</h2>
                <p className="mt-3 text-sm leading-relaxed text-gray-400">{shot.description}</p>
                <p className="mt-4 font-mono text-[11px] text-cyan/60">public/images/{shot.file}</p>
              </div>
              <Screenshot file={shot.file} alt={shot.title} />
            </div>
          ))}
        </div>
      </Section>

      <Section>
        <div className="grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
            <Layers className="mb-4 h-6 w-6 text-cyan" />
            <h3 className="font-display text-lg font-semibold text-white">Native + bridge</h3>
            <p className="mt-2 text-sm text-gray-400">
              SwiftUI for the interface, Python FastAPI for the engine. One child
              process, versioned <span className="font-mono">/v1/...</span> contract.
            </p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
            <Shield className="mb-4 h-6 w-6 text-cyan" />
            <h3 className="font-display text-lg font-semibold text-white">Loopback only</h3>
            <p className="mt-2 text-sm text-gray-400">
              127.0.0.1 with a per-launch bearer token. Offline mode refuses every
              non-loopback endpoint.
            </p>
          </div>
          <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
            <HardDrive className="mb-4 h-6 w-6 text-cyan" />
            <h3 className="font-display text-lg font-semibold text-white">Your data, one folder</h3>
            <p className="mt-2 text-sm text-gray-400">
              State, conversations, workspace and bridge venv live under{' '}
              <span className="font-mono">~/Library/Application Support/JarvisOS/</span>.
            </p>
          </div>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="rounded-3xl border border-white/5 bg-white/[0.02] p-6 md:p-10">
          <h2 className="font-display text-2xl font-semibold text-white">Architecture</h2>
          <p className="mt-2 text-sm text-gray-400">
            The macOS app owns exactly one child process and stops it on quit.
          </p>
          <pre className="mt-6 overflow-x-auto rounded-2xl border border-cyan/10 bg-void/70 p-4 text-[11px] leading-relaxed text-cyan/80">
{architecture}
          </pre>
          <a href="#/docs" className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-cyan hover:text-ice">
            Full documentation <ArrowRight size={15} />
          </a>
        </div>
      </Section>
    </div>
    </>
  )
}
