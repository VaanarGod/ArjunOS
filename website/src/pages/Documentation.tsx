import Section from '../components/ui/Section'
import { documentationSections, REPO_URL, DOCS_URL } from '../data/content'
import { ExternalLink } from 'lucide-react'

const docsLinks = [
  { label: 'Implementation status', href: `${REPO_URL}/blob/main/docs/implementation-status.md` },
  { label: 'Security model', href: `${REPO_URL}/blob/main/docs/security.md` },
  { label: 'MCP setup', href: `${REPO_URL}/blob/main/docs/mcp.md` },
  { label: 'Integration matrix', href: `${REPO_URL}/blob/main/docs/integration-matrix.md` },
  { label: 'Computer use', href: `${REPO_URL}/blob/main/docs/computer-use.md` },
  { label: 'Architecture decisions (ADRs)', href: `${REPO_URL}/tree/main/docs/architecture-decisions` },
]

export default function Documentation() {
  return (
    <>
      <Section>
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan">Documentation</p>
          <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            Everything you need to get oriented.
          </h1>
          <p className="mt-5 text-gray-400">
            Documentation lives alongside the code in the repository, so it stays
            in step with what actually ships. The full set is available at{' '}
            <a href={DOCS_URL} target="_blank" rel="noreferrer" className="font-mono text-cyan/80 hover:text-cyan">
              {DOCS_URL.replace('https://', '')}
            </a>.
          </p>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="grid gap-8 lg:grid-cols-[260px_1fr]">
          <aside className="hidden lg:block">
            <div className="sticky top-28 space-y-4">
              <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">On this page</p>
                <ul className="space-y-1">
                  {documentationSections.map((section) => (
                    <li key={section.href}>
                      <a href={section.href} className="block rounded-lg px-3 py-2 text-sm text-gray-400 transition-colors hover:bg-cyan/5 hover:text-cyan">
                        {section.title}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Deep dives</p>
                <ul className="space-y-1">
                  {docsLinks.map((link) => (
                    <li key={link.href}>
                      <a href={link.href} target="_blank" rel="noreferrer" className="flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 transition-colors hover:bg-cyan/5 hover:text-cyan">
                        <span>{link.label}</span>
                        <ExternalLink size={12} className="shrink-0 opacity-50" />
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </aside>

          <div className="space-y-6">
            {documentationSections.map((section) => (
              <div key={section.href} id={section.href.replace('#', '')} className="scroll-mt-28 rounded-2xl border border-white/5 bg-white/[0.02] p-6">
                <h2 className="font-display text-xl font-semibold text-white">{section.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-gray-400">{section.description}</p>
              </div>
            ))}

            <div className="rounded-2xl border border-cyan/15 bg-cyan/5 p-6">
              <h2 className="font-display text-xl font-semibold text-white">Full docs in the repo</h2>
              <p className="mt-2 text-sm text-gray-400">
                Every document linked above lives in{' '}
                <span className="font-mono text-cyan/80">docs/</span> inside the repository. That is the single source of truth for the project.
              </p>
              <a href={DOCS_URL} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-cyan hover:text-ice">
                Open docs/ on GitHub <ExternalLink size={13} />
              </a>
            </div>
          </div>
        </div>
      </Section>
    </>
  )
}
