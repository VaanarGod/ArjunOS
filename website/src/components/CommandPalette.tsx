import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Monitor, Book, Settings, Github, Download, Home, Code, FileText, Cpu } from 'lucide-react'
import { REPO_URL, DOWNLOAD_URL } from '../data/content'

const commandList = [
  { group: 'Navigation', items: [
    { icon: Home, label: 'Home', action: '/' },
    { icon: Cpu, label: 'Features', action: '/features' },
    { icon: Monitor, label: 'Product', action: '/product' },
    { icon: Download, label: 'Download', action: '/download' },
    { icon: Book, label: 'Documentation', action: '/docs' },
    { icon: Code, label: 'Integration Ecosystem', action: '/ecosystem' },
  ]},
  { group: 'Actions', items: [
    { icon: Download, label: 'Direct Download .dmg', action: DOWNLOAD_URL, external: true },
    { icon: Github, label: 'View GitHub Repository', action: REPO_URL, external: true },
    { icon: FileText, label: 'Read Implementation Status', action: `${REPO_URL}/blob/main/docs/implementation-status.md`, external: true },
  ]}
]

export default function CommandPalette({ isOpen, setIsOpen }: { isOpen: boolean, setIsOpen: (v: boolean) => void }) {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setIsOpen(true)
      }
      if (e.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [setIsOpen])

  const handleSelect = (item: any) => {
    setIsOpen(false)
    setQuery('')
    if (item.external) window.open(item.action, '_blank')
    else navigate(item.action)
  }

  const filtered = commandList.map(group => ({
    ...group,
    items: group.items.filter(item => item.label.toLowerCase().includes(query.toLowerCase()))
  })).filter(group => group.items.length > 0)

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]" onClick={() => setIsOpen(false)} />
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} transition={{ duration: 0.2 }} className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg z-[101]">
            <div className="glass-strong rounded-2xl overflow-hidden shadow-[0_0_50px_rgba(34,211,238,0.15)] border border-cyan/20">
              <div className="flex items-center px-4 border-b border-white/10">
                <Search className="w-5 h-5 text-gray-500 mr-3" />
                <input autoFocus type="text" placeholder="Search commands..." value={query} onChange={(e) => setQuery(e.target.value)} className="w-full bg-transparent text-white placeholder-gray-500 py-4 outline-none text-sm" />
                <kbd className="hidden sm:inline-block text-[10px] font-mono text-gray-500 border border-white/10 px-2 py-0.5 rounded">ESC</kbd>
              </div>
              <div className="max-h-[300px] overflow-y-auto p-2">
                {filtered.length === 0 && <div className="p-4 text-center text-sm text-gray-500">No commands found.</div>}
                {filtered.map((group) => (
                  <div key={group.group} className="mb-2">
                    <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">{group.group}</div>
                    {group.items.map((item) => (
                      <button key={item.label} onClick={() => handleSelect(item)} className="w-full text-left flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-cyan/10 hover:text-cyan transition-colors group">
                        <item.icon className="w-4 h-4 text-gray-500 group-hover:text-cyan" />
                        {item.label}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
