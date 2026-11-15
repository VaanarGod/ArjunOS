import { ReactNode } from 'react'
import { motion } from 'framer-motion'

export default function Section({
  children,
  className = '',
  id,
}: {
  children: ReactNode
  className?: string
  id?: string
}) {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-100px' }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className={`relative mx-auto max-w-6xl px-6 py-20 md:py-28 ${className}`}
    >
      {children}
    </motion.section>
  )
}
