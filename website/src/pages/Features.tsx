import { motion } from 'framer-motion'
import Section from '../components/ui/Section'
import StatusBadge from '../components/ui/StatusBadge'
import { features, roadmap } from '../data/content'
import {
  MessageSquare, Users, Globe, Search, Database, UserRound,
  Plug, FileText, BookOpen, Sparkles, Terminal, FolderPlus,
  Palette, Shield,
} from 'lucide-react'

const iconMap = {
  MessageSquare, Users, Globe, Search, Database, UserRound,
  Plug, FileText, BookOpen, Sparkles, Terminal, FolderPlus,
  Palette, Shield,
} as const

export default function Features() {
  return (
    <>
      <div className="pointer-events-none fixed inset-0 bg-holographic-grid opacity-40 z-0" />
      <div className="relative z-10">
      <Section>
        <div className="max-w-2xl">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan">Capabilities</p>
          <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl">What is actually built.</h1>
          <p className="mt-5 text-gray-400">
            Feature status is shown honestly. Anything marked “Partial”,
            “Planned” or “Not built” is not something you should expect to work
            today. The full implementation-status document lives in the
            repository at <span className="font-mono text-cyan/80">docs/implementation-status.md</span>.
          </p>
        </div>
      </Section>

      <Section className="pt-0">
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, i) => {
            const Icon = iconMap[feature.icon as keyof typeof iconMap] ?? Shield
            return (
              <motion.article
                key={feature.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.04, duration: 0.5 }}
                className="group relative overflow-hidden rounded-2xl border border-white/5 bg-white/[0.02] p-6 transition-colors hover:border-cyan/20"
              >
                <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-cyan/5 blur-2xl" />
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan/20 bg-cyan/5 text-cyan">
                    <Icon size={19} />
                  </div>
                  <StatusBadge status={feature.status} />
                </div>
                <h2 className="font-display text-lg font-semibold text-white">{feature.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-gray-400">{feature.description}</p>
              </motion.article>
            )
          })}
        </div>
      </Section>

      <Section className="pt-0">
        <div className="rounded-3xl border border-violet/20 bg-violet/5 p-8">
          <h2 className="font-display text-2xl font-semibold text-white">Not built yet</h2>
          <p className="mt-2 text-sm text-gray-400">
            These are on the roadmap and are not part of the current build. The
            website will not pretend otherwise.
          </p>
          <ul className="mt-5 grid gap-3 sm:grid-cols-2">
            {roadmap.map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm text-gray-300">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-violet" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </Section>
    </div>
    </>
  )
}
