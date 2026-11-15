import { useState } from 'react'
import Section from '../components/ui/Section'
import Scene3D from '../components/three/Scene3D'
import { integrations } from '../data/content'
import { motion, AnimatePresence } from 'framer-motion'
import { Cpu, Cloud, Plug, Mic, BookOpen, X, ExternalLink, Activity } from 'lucide-react'

const statusColors = {
  'Implemented': 'text-cyan border-cyan/30 bg-cyan/10',
  'Planned': 'text-violet border-violet/30 bg-violet/10',
  'In development': 'text-yellow-400 border-yellow-400/30 bg-yellow-400/10',
}

export default function Ecosystem() {
  const [selected, setSelected] = useState<typeof integrations[number] | null>(null)
  const [filter, setFilter] = useState('All')

  const categories = ['All', 'Local Inference', 'Cloud AI', 'Tools', 'Speech', 'Automation']
  const filtered = filter === 'All' ? integrations : integrations.filter(i => i.category === filter)

  return (
    <>
      <div className="fixed inset-0 z-0"><Scene3D variant="galaxy" /></div>
      <div className="relative z-10">
        <Section>
          <div className="max-w-2xl mb-12">
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan">Integration Ecosystem</p>
            <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              The connected architecture.
            </h1>
            <p className="mt-5 text-gray-400">
              Explore how ArjunOS connects to local models, external APIs, and your local system. 
              Integrations are listed with their honest implementation status.
            </p>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2 mb-8">
            {categories.map(c => (
              <button key={c} onClick={() => setFilter(c)} className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${filter === c ? 'bg-cyan text-void' : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white border border-white/10'}`}>
                {c}
              </button>
            ))}
          </div>

          {/* Grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 relative">
            {filtered.map((item) => (
              <motion.button
                key={item.id}
                layoutId={`card-${item.id}`}
                onClick={() => setSelected(item)}
                className="group relative text-left p-6 rounded-2xl border border-white/5 bg-[#050505]/80 backdrop-blur-md hover:border-cyan/30 transition-all flex flex-col justify-between h-40"
              >
                <div className="flex items-start justify-between w-full">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/5 text-cyan">
                    <Activity size={18} />
                  </div>
                  <span className={`text-[10px] uppercase tracking-wider px-2 py-1 rounded border ${statusColors[item.status as keyof typeof statusColors] || 'text-gray-400 border-white/10'}`}>
                    {item.status}
                  </span>
                </div>
                <div>
                  <h3 className="font-display text-lg font-semibold text-white group-hover:text-cyan transition-colors">{item.name}</h3>
                  <p className="text-xs text-gray-500 uppercase tracking-wider mt-1">{item.category}</p>
                </div>
              </motion.button>
            ))}
          </div>
        </Section>
      </div>

      {/* Detail Modal */}
      <AnimatePresence>
        {selected && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100]" onClick={() => setSelected(null)} />
            <motion.div layoutId={`card-${selected.id}`} className="fixed inset-0 m-auto w-full max-w-md h-fit max-h-[80vh] overflow-y-auto glass-strong rounded-3xl p-8 z-[101] shadow-[0_0_80px_rgba(34,211,238,0.1)] border border-cyan/20">
              <button onClick={() => setSelected(null)} className="absolute top-6 right-6 text-gray-500 hover:text-white"><X size={20} /></button>
              
              <div className="flex items-center gap-3 mb-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-cyan/10 text-cyan">
                  <Activity size={24} />
                </div>
                <div>
                  <h2 className="font-display text-2xl font-semibold text-white">{selected.name}</h2>
                  <p className="text-xs text-gray-400">{selected.category}</p>
                </div>
              </div>

              <div className="mb-6">
                <span className={`text-xs uppercase tracking-wider px-2 py-1 rounded border ${statusColors[selected.status as keyof typeof statusColors]}`}>
                  {selected.status}
                </span>
              </div>

              <p className="text-sm text-gray-300 leading-relaxed mb-8">
                {selected.desc}
              </p>

              <div className="flex gap-4 border-t border-white/10 pt-6">
                <button className="flex items-center gap-2 text-xs font-medium text-cyan hover:text-ice transition-colors">
                  View Docs <ExternalLink size={12} />
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
