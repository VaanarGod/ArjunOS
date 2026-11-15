import { ReactNode } from 'react'
import { motion } from 'framer-motion'

export default function GlassCard({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
      className={`glass rounded-2xl p-6 transition-shadow hover:shadow-glow ${className}`}
    >
      {children}
    </motion.div>
  )
}
