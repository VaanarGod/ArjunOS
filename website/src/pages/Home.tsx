import { lazy, Suspense } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Download, Shield, Cpu, Layers, Sparkles, MessageSquare, Users, Database } from 'lucide-react'
import Section from '../components/ui/Section'
import GlassCard from '../components/ui/GlassCard'
import MagneticButton from '../components/ui/MagneticButton'
import Screenshot from '../components/ui/Screenshot'
import { features, techStack, APP_VERSION, APP_STATUS, REPO_URL, DOWNLOAD_URL, screenshots } from '../data/content'

const AICore = lazy(() => import('../components/three/AICore'))

export default function Home() {
  return (
    <>
      <section className="relative flex min-h-[92vh] items-center overflow-hidden">
        <div className="absolute inset-0 grid-bg opacity-20" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-void/50 to-void z-10 pointer-events-none" />
        <div className="absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan/10 blur-[150px]" />

        <div className="relative z-20 mx-auto grid w-full max-w-6xl items-center gap-12 px-6 lg:grid-cols-2 pointer-events-auto">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-cyan/20 bg-cyan/5 px-3 py-1.5 text-xs text-cyan">
              <Sparkles size={13} />
              v{APP_VERSION} · {APP_STATUS} · macOS 14+
            </div>

            <h1 className="font-display text-5xl font-semibold leading-[1.05] tracking-tight text-white sm:text-6xl lg:text-7xl">
              Your AI.
              <br />
              Your Machine.
              <br />
              <span className="text-gradient">Your Intelligence.</span>
            </h1>

            <p className="mt-6 max-w-lg text-base leading-relaxed text-gray-400 sm:text-lg">
              ArjunOS is a local-first personal AI operating system for macOS.
              A native SwiftUI app backed by a Python bridge, bringing local
              models, agents, tools, memory, and browser into one unified
              experience.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-4">
              <MagneticButton
                href={DOWNLOAD_URL}
                className="bg-cyan text-void shadow-glow-strong hover:bg-ice"
              >
                <Download size={16} />
                Download ArjunOS
              </MagneticButton>
              <MagneticButton href="#/features" className="border border-white/10 bg-white/5 text-white hover:border-cyan/30 hover:bg-cyan/5">
                Explore Features
                <ArrowRight size={16} />
              </MagneticButton>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-5 text-xs text-gray-500">
              <span className="flex items-center gap-1.5"><Shield size={13} className="text-cyan" /> Local-first by design</span>
              <span className="flex items-center gap-1.5"><Cpu size={13} className="text-cyan" /> Ollama / llama.cpp / LM Studio</span>
              <span className="flex items-center gap-1.5"><Layers size={13} className="text-cyan" /> Apache-2.0</span>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1.2, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="relative h-[380px] w-full sm:h-[460px] lg:h-[520px]"
          >
            {/* Scale the canvas wrapper up and overflow the container to avoid hard clipping */}
            <div className="pointer-events-none absolute inset-[-20%] sm:inset-[-30%] lg:inset-[-40%] z-0">
              <Suspense fallback={<div className="h-full w-full" />}>
                <AICore />
              </Suspense>
            </div>
            <div className="pointer-events-none absolute inset-0 rounded-full border border-cyan/5" />
          </motion.div>
        </div>
      </section>

      <Section className="py-10 md:py-12">
        <div className="grid gap-4 rounded-2xl border border-white/5 bg-white/[0.02] p-6 sm:grid-cols-2 lg:grid-cols-4">
          {techStack.map((item) => (
            <div key={item.label}>
              <p className="text-xs uppercase tracking-wider text-gray-500">{item.label}</p>
              <p className="mt-1 text-sm font-medium text-white">{item.value}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section>
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan">One unified environment</p>
          <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            A personal AI system that feels like part of your Mac.
          </h2>
          <p className="mt-5 text-gray-400">
            ArjunOS is a real macOS application. The chat core, safety layer,
            memory, MCP, web search, file reading and the interface have been
            run on a Mac. Voice, scheduling, plugins, a setup wizard and cloud
            providers are not built yet — and the website will say so honestly.
          </p>
        </div>
      </Section>

      <Section>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { icon: MessageSquare, id: 'local-chat' },
            { icon: Users, id: 'crew' },
            { icon: Database, id: 'memory' },
          ].map(({ icon: Icon, id }) => {
            const feature = features.find((f) => f.id === id)
            if (!feature) return null
            return (
              <GlassCard key={id} className="group">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-cyan/20 bg-cyan/5 text-cyan">
                  <Icon size={18} />
                </div>
                <h3 className="font-display text-lg font-semibold text-white">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-400">{feature.description}</p>
              </GlassCard>
            )
          })}
        </div>
        <div className="mt-8 text-center">
          <Link to="/features" className="inline-flex items-center gap-2 text-sm font-medium text-cyan hover:text-ice">
            View all features <ArrowRight size={15} />
          </Link>
        </div>
      </Section>

      <Section>
        <div className="mb-8 flex items-end justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan">Screenshots</p>
            <h2 className="mt-3 font-display text-3xl font-semibold text-white">The macOS app, up close.</h2>
          </div>
          <Link to="/product" className="hidden text-sm font-medium text-cyan hover:text-ice sm:inline-flex sm:items-center sm:gap-2">
            See all screenshots <ArrowRight size={15} />
          </Link>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {screenshots.slice(0, 3).map((shot) => (
            <div key={shot.file} className="space-y-3">
              <Screenshot file={shot.file} alt={shot.title} />
              <p className="px-1 text-sm font-medium text-white">{shot.title}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section>
        <div className="glass overflow-hidden rounded-3xl p-8 md:p-14">
          <div className="grid items-center gap-10 md:grid-cols-2">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan">Local-first AI</p>
              <h2 className="mt-4 font-display text-3xl font-semibold text-white">Your data stays on your machine.</h2>
              <p className="mt-4 text-gray-400">
                The bridge listens on <span className="font-mono text-cyan/80">127.0.0.1</span> only
                and uses a per-launch bearer token. Offline mode refuses every
                non-loopback endpoint. Every tool call needs a fresh approval.
              </p>
              <ul className="mt-6 space-y-3 text-sm text-gray-300">
                <li className="flex items-start gap-2"><span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-cyan" />Models you already run — Ollama, LM Studio, llama.cpp, vLLM</li>
                <li className="flex items-start gap-2"><span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-cyan" />Local SQLite FTS5 memory, credential stores never read</li>
                <li className="flex items-start gap-2"><span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-cyan" />One approval per action, expires after 5 minutes</li>
              </ul>
            </div>
            <div className="relative flex aspect-square items-center justify-center rounded-2xl border border-cyan/10 bg-void/50">
              <div className="absolute inset-8 rounded-full border border-cyan/10" />
              <div className="absolute inset-16 rounded-full border border-cyan/10" />
              <div className="h-24 w-24 rounded-full bg-cyan/10 blur-2xl" />
              <Shield className="relative h-16 w-16 text-cyan/70" strokeWidth={1} />
            </div>
          </div>
        </div>
      </Section>

      <Section>
        <div className="grid gap-10 md:grid-cols-2">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-violet">Native app + Python bridge</p>
            <h2 className="mt-4 font-display text-3xl font-semibold text-white">SwiftUI on the front, Python on the engine.</h2>
            <p className="mt-4 text-gray-400">
              A native SwiftUI app for the interface, with a versioned local
              HTTP API to a Python FastAPI bridge. The app owns exactly one
              child process, starts it with a minimal environment, and stops it
              on quit.
            </p>
            <Link to="/docs" className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-violet hover:text-white">
              Read the documentation <ArrowRight size={15} />
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              ['SwiftUI app', 'JarvisCore + JarvisOS'],
              ['FastAPI bridge', 'discovery → providers → orchestrator'],
              ['Crew', 'Multi-model orchestration'],
              ['MCP', 'One JSON file per server'],
            ].map(([title, desc]) => (
              <div key={title} className="rounded-xl border border-white/5 bg-white/[0.02] p-5">
                <h4 className="text-sm font-semibold text-white">{title}</h4>
                <p className="mt-1 text-xs text-gray-500">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </Section>

      <Section className="pb-32">
        <div className="relative overflow-hidden rounded-3xl border border-cyan/20 bg-gradient-to-br from-cyan/10 via-midnight to-violet/10 p-10 text-center md:p-16">
          <div className="pointer-events-none absolute inset-0 grid-bg opacity-20" />
          <h2 className="relative font-display text-3xl font-semibold text-white sm:text-4xl">Bring your AI home.</h2>
          <p className="relative mx-auto mt-4 max-w-xl text-gray-400">
            ArjunOS v{APP_VERSION} is an early build. Get the code, build it on
            your Mac, and try it with the models you already run.
          </p>
          <div className="relative mt-8 flex flex-wrap justify-center gap-4">
            <MagneticButton href="#/download" className="bg-cyan text-void hover:bg-ice">
              <Download size={16} /> Download
            </MagneticButton>
            <MagneticButton href={REPO_URL} className="border border-white/10 bg-white/5 text-white hover:border-cyan/30">
              View on GitHub
            </MagneticButton>
          </div>
        </div>
      </Section>
    </>
  )
}
