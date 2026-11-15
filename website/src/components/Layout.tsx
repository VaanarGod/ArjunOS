import { ReactNode } from 'react'
import Navbar from './Navbar'
import Footer from './Footer'

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-screen bg-void text-gray-200">
      <div className="pointer-events-none fixed inset-0 grid-bg opacity-40" />
      <div className="pointer-events-none fixed left-1/2 top-0 h-[600px] w-[900px] -translate-x-1/2 radial-fade" />
      <Navbar />
      <main className="relative pt-24">{children}</main>
      <Footer />
    </div>
  )
}
