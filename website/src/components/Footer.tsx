import { Link } from 'react-router-dom'
import { Github } from 'lucide-react'
import { REPO_URL, LICENSE, LICENSE_URL, APP_VERSION } from '../data/content'

export default function Footer() {
  return (
    <footer className="relative mt-32 border-t border-white/5 bg-midnight/40">
      <div className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid gap-10 md:grid-cols-4">
          <div className="md:col-span-2">
            <Link to="/" className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan/30 bg-cyan/10">
                <div className="h-4 w-4 rounded-full bg-cyan" />
              </div>
              <span className="font-display text-lg font-semibold text-white">
                Arjun<span className="text-cyan">OS</span>
              </span>
            </Link>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-gray-400">
              A local-first personal AI operating system for macOS. Native
              SwiftUI app with a tested Python bridge — your models, your Mac,
              your data.
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-4 text-sm">
              <a href={REPO_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-gray-400 transition-colors hover:text-cyan">
                <Github size={16} />
                View repository
              </a>
              <a href={LICENSE_URL} target="_blank" rel="noreferrer" className="text-gray-500 transition-colors hover:text-cyan">
                {LICENSE}
              </a>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-white">Product</h4>
            <ul className="mt-4 space-y-2 text-sm text-gray-400">
              <li><Link to="/features" className="hover:text-cyan">Features</Link></li>
              <li><Link to="/product" className="hover:text-cyan">Product</Link></li>
              <li><Link to="/download" className="hover:text-cyan">Download</Link></li>
              <li><Link to="/changelog" className="hover:text-cyan">Changelog</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-white">Resources</h4>
            <ul className="mt-4 space-y-2 text-sm text-gray-400">
              <li><Link to="/docs" className="hover:text-cyan">Documentation</Link></li>
              <li><Link to="/about" className="hover:text-cyan">About</Link></li>
              <li><a href={REPO_URL} target="_blank" rel="noreferrer" className="hover:text-cyan">GitHub</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-4 border-t border-white/5 pt-6 text-xs text-gray-500 sm:flex-row sm:items-center">
          <p>© {new Date().getFullYear()} ArjunOS · v{APP_VERSION} · {LICENSE}</p>
          <p className="text-gray-600">ArjunOS is a separate macOS application. This website is a product showcase.</p>
        </div>
      </div>
    </footer>
  )
}
