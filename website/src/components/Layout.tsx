import { ReactNode } from 'react'
import Navbar from './Navbar'
import Footer from './Footer'

export default function Layout({ children, onSearchClick }: { children: ReactNode, onSearchClick: () => void }) {
  return (
    <div className="relative min-h-screen bg-void text-gray-200">
      <div className="pointer-events-none fixed inset-0 grid-bg opacity-30" />
      <Navbar onSearchClick={onSearchClick} />
      <main className="relative pt-24">{children}</main>
      <Footer />
    </div>
  )
}
