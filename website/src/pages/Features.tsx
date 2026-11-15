import { motion } from 'framer-motion'
import Section from '../components/ui/Section'
import Scene3D from '../components/three/Scene3D'
import { features } from '../data/content'
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

// --- CUSTOM MICRO-VISUALS FOR FEATURES ---
function NeuralVisual() {
  return (
    <div className="flex items-center justify-center h-full gap-2 opacity-70">
      <svg width="100" height="40" viewBox="0 0 100 40" className="text-cyan">
        <path d="M10 20 L40 10 L70 30 L90 20" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="4 4" className="animate-data-flow" />
        <path d="M10 20 L40 30 L70 10 L90 20" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="4 4" className="animate-data-flow" style={{ animationDirection: 'reverse' }} />
        <circle cx="10" cy="20" r="2" fill="currentColor" />
        <circle cx="40" cy="10" r="2" fill="currentColor" />
        <circle cx="40" cy="30" r="2" fill="currentColor" />
        <circle cx="70" cy="10" r="2" fill="currentColor" />
        <circle cx="70" cy="30" r="2" fill="currentColor" />
        <circle cx="90" cy="20" r="2" fill="currentColor" />
      </svg>
    </div>
  )
}

function VoiceVisual() {
  return (
    <div className="flex items-center justify-center h-full gap-1 text-cyan opacity-80">
      {[1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className="w-1.5 bg-current rounded-full animate-soundwave"
          style={{ height: '30px', animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  )
}

function SecurityVisual() {
  return (
    <div className="flex items-center justify-center h-full relative opacity-80">
      <div className="absolute inset-0 rounded-full bg-cyan/5 blur-xl" />
      <Shield className="w-12 h-12 text-cyan/60" strokeWidth={1} />
    </div>
  )
}

export default function Features() {
  const primaryFeatures = features.filter(f => ['local-chat', 'crew', 'memory', 'privacy'].includes(f.id))
  const secondaryFeatures = features.filter(f => !['local-chat', 'crew', 'memory', 'privacy'].includes(f.id))

  return (
    <>
      <div className="fixed inset-0 z-0"><Scene3D variant="neural" /></div>
      
      <div className="relative z-10">
        <Section>
          <div className="max-w-2xl mb-12">
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan">Capabilities</p>
            <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              The ArjunOS Ecosystem.
            </h1>
            <p className="mt-5 text-gray-400">
              Every capability is built to operate within the same local-first environment. 
              Status is shown honestly — anything marked “Partial” or “Design principle” 
              reflects the actual state of the codebase.
            </p>
          </div>

          {/* PRIMARY FEATURES (Bento Box / Large) */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-6">
            {primaryFeatures.map((feature, i) => {
              const Icon = iconMap[feature.icon as keyof typeof iconMap] || Shield
              const isLarge = i === 0 // Make the first one span 2 columns
              return (
                <motion.div
                  key={feature.id}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1, duration: 0.5 }}
                  className={`group relative overflow-hidden rounded-3xl border border-white/10 bg-[#050505]/95 backdrop-blur-xl p-8 shadow-2xl transition-all hover:border-cyan/30 ${
                    isLarge ? 'md:col-span-2' : ''
                  }`}
                >
                  <div className="absolute top-0 right-0 p-8 opacity-20 group-hover:opacity-40 transition-opacity">
                     {feature.id === 'local-chat' ? <NeuralVisual /> : 
                      feature.id === 'privacy' ? <SecurityVisual /> : 
                      <Icon size={80} strokeWidth={0.5} />}
                  </div>
                  
                  <div className="relative z-10 flex flex-col h-full justify-between">
                    <div>
                      <div className="flex items-center gap-3 mb-6">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5 border border-white/10 text-cyan">
                          <Icon size={20} />
                        </div>
                        <span className="text-xs font-mono text-cyan/80 border border-cyan/20 px-2 py-0.5 rounded bg-cyan/5">
                          {feature.status}
                        </span>
                      </div>
                      <h2 className="font-display text-2xl font-semibold text-white mb-2">{feature.title}</h2>
                      <p className="text-gray-400 text-sm leading-relaxed max-w-md">{feature.description}</p>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </div>

          {/* SECONDARY FEATURES (Smaller, more compact) */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {secondaryFeatures.map((feature, i) => {
              const Icon = iconMap[feature.icon as keyof typeof iconMap] || Shield
              return (
                <motion.div
                  key={feature.id}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05, duration: 0.4 }}
                  className="group relative overflow-hidden rounded-2xl border border-white/5 bg-[#080808]/90 p-6 transition-all hover:bg-[#0a0a0a] hover:border-white/20"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex shrink-0 h-10 w-10 items-center justify-center rounded-lg bg-white/5 text-gray-400 group-hover:text-cyan transition-colors">
                      <Icon size={18} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-display text-base font-semibold text-white">{feature.title}</h3>
                        {feature.id === 'voice' && <span className="w-2 h-2 rounded-full bg-cyan animate-pulse" title="Visualizer active" />}
                      </div>
                      <p className="text-xs text-gray-500 leading-relaxed">{feature.description}</p>
                    </div>
                  </div>
                  
                  {feature.id === 'voice' && (
                    <div className="absolute right-4 bottom-4 h-8 w-12 opacity-50">
                      <VoiceVisual />
                    </div>
                  )}
                </motion.div>
              )
            })}
          </div>
        </Section>
      </div>
    </>
  )
}
