import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X, Download, Github, Search } from 'lucide-react'
import { DOWNLOAD_URL, REPO_URL } from '../data/content'

const links = [
  { to: '/', label: 'Home' },
  { to: '/features', label: 'Features' },
  { to: '/product', label: 'Product' },
  { to: '/ecosystem', label: 'Ecosystem' },
  { to: '/docs', label: 'Docs' },
  { to: '/changelog', label: 'Changelog' },
  { to: '/about', label: 'About' },
]

export default function Navbar({ onSearchClick }: { onSearchClick: () => void }) {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => setOpen(false), [location.pathname])

  return (
    <header className="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-4">
      <motion.nav
        initial={false}
        animate={{
          backgroundColor: scrolled ? 'rgba(0, 0, 0, 0.8)' : 'rgba(0, 0, 0, 0)',
          borderColor: scrolled ? 'rgba(34, 211, 238, 0.16)' : 'rgba(34, 211, 238, 0)',
          backdropFilter: scrolled ? 'blur(20px)' : 'blur(0px)',
        }}
        transition={{ duration: 0.3 }}
        className="flex w-full max-w-6xl items-center justify-between rounded-2xl border px-5 py-3"
      >
        <Link to="/" className="group flex items-center gap-3">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-cyan/30 bg-cyan/10">
            <div className="h-4 w-4 rounded-full bg-cyan shadow-[0_0_18px_rgba(34,211,238,0.8)]" />
            <div className="absolute inset-0 rounded-xl border border-cyan/20 animate-pulse-slow" />
          </div>
          <span className="font-display text-lg font-semibold tracking-tight text-white">
            Arjun<span className="text-cyan">OS</span>
          </span>
        </Link>

        <div className="hidden items-center gap-1 lg:flex">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `relative rounded-lg px-3 py-2 text-sm font-medium transition-colors ${isActive ? 'text-white' : 'text-gray-400 hover:text-white'}`
              }
            >
              {({ isActive }) => (
                <>
                  {link.label}
                  {isActive && (
                    <motion.span layoutId="nav-underline" className="absolute inset-x-2 -bottom-0.5 h-px bg-gradient-to-r from-transparent via-cyan to-transparent" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {/* Command Palette Trigger */}
          <button
            onClick={onSearchClick}
            className="flex items-center gap-2 px-3 py-2 rounded-xl border border-white/10 bg-white/5 text-gray-400 hover:text-white hover:border-cyan/30 transition-all text-sm font-medium"
          >
            <Search size={16} />
            <span className="hidden sm:inline-block">Search</span>
            <kbd className="hidden sm:inline-block ml-2 text-[10px] font-mono border border-white/10 px-1.5 py-0.5 rounded">⌘K</kbd>
          </button>

          <a href={REPO_URL} target="_blank" rel="noreferrer" className="hidden sm:flex items-center justify-center rounded-xl border border-white/10 bg-white/5 p-2.5 text-gray-300 transition-all hover:border-cyan/30 hover:bg-cyan/10 hover:text-cyan" aria-label="GitHub Repository">
            <Github size={18} className="transition-transform group-hover:scale-110" />
          </a>

          <a href={DOWNLOAD_URL} className="group relative hidden items-center gap-2 overflow-hidden rounded-xl border border-cyan/40 bg-cyan/10 px-4 py-2 text-sm font-semibold text-cyan transition-all hover:bg-cyan/20 sm:flex">
            <Download size={15} />
            <span>Download</span>
            <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
          </a>
          
          <button onClick={() => setOpen(!open)} className="rounded-lg border border-white/10 p-2 text-gray-300 lg:hidden">
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </motion.nav>

      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} className="absolute left-4 right-4 top-20 z-50 rounded-2xl border border-cyan/15 bg-black/95 p-4 backdrop-blur-2xl lg:hidden">
            <div className="flex flex-col gap-1">
              {links.map((link) => (
                <NavLink key={link.to} to={link.to} className={({ isActive }) => `rounded-lg px-4 py-3 text-sm font-medium ${isActive ? 'bg-cyan/10 text-cyan' : 'text-gray-300'}`}>
                  {link.label}
                </NavLink>
              ))}
              <a href={DOWNLOAD_URL} className="mt-2 flex items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-3 text-sm font-semibold text-void">
                <Download size={16} /> Download ArjunOS
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
