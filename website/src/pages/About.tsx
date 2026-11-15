import Section from '../components/ui/Section'
import Scene3D from '../components/three/Scene3D'
import { Shield, Cpu, Layers, Github, Lock, Boxes, Code2, FileCode2 } from 'lucide-react'
import { REPO_URL, LICENSE, LICENSE_URL, DOCS_URL } from '../data/content'

const values = [
  {
    title: 'Personal AI ownership',
    description:
      'Your AI should belong to you, not to a platform. ArjunOS runs on your Mac, uses models you already have, and stores its state in one folder you can copy or delete.',
    icon: Lock,
  },
  {
    title: 'Local-first intelligence',
    description:
      'Local inference and local storage are first-class. Ollama, LM Studio, llama.cpp, vLLM and OpenAI-compatible servers are all first-class. Cloud providers are deliberately blocked today.',
    icon: Cpu,
  },
  {
    title: 'Privacy',
    description:
      'The bridge listens on 127.0.0.1 with a per-launch bearer token. Credential stores are never read. One approval per tool call, expiring after five minutes.',
    icon: Shield,
  },
  {
    title: 'Extensibility',
    description:
      'Models are discovered automatically. MCP servers connect through one JSON file each. Crew composes multiple models into a small team.',
    icon: Layers,
  },
  {
    title: 'Open source',
    description:
      'Apache-2.0 licensed. Built with Swift, Python, FastAPI and mature open-source libraries for PDFs, SQLite FTS and HTTP.',
    icon: Github,
  },
  {
    title: 'One unified environment',
    description:
      'Chat, browser, memory, profile, files, terminal, Crew and Obsidian live in one app instead of scattered across services.',
    icon: Boxes,
  },
]

export default function About() {
  return (
    <>
      <div className="fixed inset-0 z-0"><Scene3D variant="galaxy" /></div>
      <div className="pointer-events-none fixed inset-0 bg-about-space z-0" />
      <div className="relative z-10">
      <Section>
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan">About</p>
          <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            The vision behind ArjunOS.
          </h1>
          <p className="mt-5 text-gray-400">
            ArjunOS is a local-first personal AI assistant for macOS. A native
            SwiftUI app with a tested Python bridge — your models, your Mac,
            your data. Licensed under {LICENSE}.
          </p>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {values.map((value) => (
            <div key={value.title} className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-cyan/20 bg-cyan/5 text-cyan">
                <value.icon size={18} />
              </div>
              <h2 className="font-display text-base font-semibold text-white">{value.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-400">{value.description}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section className="pt-0">
        <div className="grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl border border-white/5 bg-white/[0.02] p-8">
            <Code2 className="mb-4 h-6 w-6 text-cyan" />
            <h2 className="font-display text-xl font-semibold text-white">Native macOS + Python bridge</h2>
            <p className="mt-2 text-sm text-gray-400">
              Swift gives a native app; Python has mature libraries for PDFs,
              SQLite FTS and HTTP. The seam is a versioned local HTTP API
              (<span className="font-mono">/v1/...</span>). The app owns exactly
              one child process and stops it on quit.
            </p>
          </div>
          <div className="rounded-3xl border border-white/5 bg-white/[0.02] p-8">
            <FileCode2 className="mb-4 h-6 w-6 text-cyan" />
            <h2 className="font-display text-xl font-semibold text-white">Honest about status</h2>
            <p className="mt-2 text-sm text-gray-400">
              The README states what is verified, mocked, unbuilt or missing.
              Features marked “Partial”, “Planned” or “Not built” are not
              presented on this site as if they work today.
            </p>
            <a href={`${REPO_URL}/blob/main/docs/implementation-status.md`} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-cyan hover:text-ice">
              Read implementation-status.md →
            </a>
          </div>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="glass rounded-3xl p-8 md:p-12">
          <div className="flex flex-col items-start gap-6 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="font-display text-2xl font-semibold text-white">Follow the project</h2>
              <p className="mt-2 max-w-lg text-sm text-gray-400">
                ArjunOS is developed in the open. Visit the repository to read
                the code, report issues, and follow progress toward the next
                build.
              </p>
              <p className="mt-3 text-xs text-gray-500">
                License:{' '}
                <a href={LICENSE_URL} target="_blank" rel="noreferrer" className="font-mono text-cyan/70 hover:text-cyan">{LICENSE}</a>
                {' · '}
                <a href={DOCS_URL} target="_blank" rel="noreferrer" className="font-mono text-cyan/70 hover:text-cyan">docs/</a>
              </p>
            </div>
            <a href={REPO_URL} target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-cyan px-6 py-3 text-sm font-semibold text-void transition-colors hover:bg-ice">
              <Github size={16} /> Open GitHub repository
            </a>
          </div>
        </div>
      </Section>
    </div>
    </>
  )
}
