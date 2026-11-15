import Section from '../components/ui/Section'
import Scene3D from '../components/three/Scene3D'
import { GitBranch, CheckCircle2, Clock } from 'lucide-react'
import { APP_VERSION, REPO_URL, RELEASES_URL } from '../data/content'

const released = [
  'Local chat — Ollama, LM Studio, llama.cpp, vLLM and any OpenAI-compatible server',
  'Crew — boss + worker orchestration with per-worker browser panels',
  'Built-in browser with page reading as primary source',
  'Web search (DuckDuckGo) with permission gating',
  'Memory — SQLite FTS5, undoable, no secrets stored',
  'Profile — name, answer style, standing instructions, live token meter',
  'MCP tools via one JSON file per server',
  'File reading — PDF, Word, Excel, PowerPoint, OpenDocument, RTF, EPUB, SQLite, archives, images',
  'Obsidian vault search and write-into-own-folder',
  'Floating assistant / pet on a global shortcut',
  'Sandboxed terminal with an allow-list and Seatbelt for node',
  'Create files in the workspace folder (never overwrites)',
  'Rich answers — Markdown, tables, Copy on code, KaTeX math',
]

const next = [
  'Computer use — Swift side not yet compiled and verified by the author',
  'Voice (speech-to-text and text-to-speech)',
  'Scheduled jobs and routines',
  'Plugins and skills',
  'First-run setup wizard',
  'Knowledge-base indexing of whole folders',
  'Cloud providers (deliberately blocked today)',
]

export default function Changelog() {
  return (
    <>
      <div className="fixed inset-0 z-0"><Scene3D variant="timeline" /></div>
      <div className="pointer-events-none fixed inset-0 bg-changelog-glow z-0" />
      <div className="relative z-10">
      <Section>
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan">Changelog</p>
          <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            Release history.
          </h1>
          <p className="mt-5 text-gray-400">
            Every entry below is drawn from the actual project state. Nothing is
            fabricated. See{' '}
            <a href={`${REPO_URL}/blob/main/docs/implementation-status.md`} target="_blank" rel="noreferrer" className="font-mono text-cyan/80 hover:text-cyan">
              docs/implementation-status.md
            </a>{' '}
            for the authoritative version.
          </p>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="space-y-6">
          <div className="rounded-3xl border border-cyan/15 bg-white/[0.02] p-8 md:p-10">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan/20 bg-cyan/5 text-cyan">
                <GitBranch size={18} />
              </div>
              <h2 className="font-display text-2xl font-semibold text-white">v{APP_VERSION}</h2>
              <span className="rounded-full bg-cyan/10 px-2.5 py-1 text-[11px] font-medium text-cyan">Early build</span>
            </div>

            <div className="mt-6 grid gap-8 md:grid-cols-2">
              <div>
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
                  <CheckCircle2 size={15} className="text-cyan" /> Shipped
                </div>
                <ul className="space-y-2 text-sm text-gray-400">
                  {released.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
                  <Clock size={15} className="text-violet" /> Not built yet
                </div>
                <ul className="space-y-2 text-sm text-gray-400">
                  {next.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-violet" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <a href={RELEASES_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-xl border border-cyan/30 bg-cyan/10 px-4 py-2 text-sm font-semibold text-cyan transition-colors hover:bg-cyan/20">
                GitHub Releases
              </a>
              <a href={REPO_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition-colors hover:border-cyan/30">
                Repository
              </a>
            </div>
          </div>

          <div className="rounded-3xl border border-dashed border-white/10 bg-white/[0.01] p-8 text-center">
            <p className="text-sm text-gray-500">Previous releases will appear here as new versions ship.</p>
          </div>
        </div>
      </Section>
    </div>
    </>
  )
}
