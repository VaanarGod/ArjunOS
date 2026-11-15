import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { lazy, Suspense } from 'react'
import Layout from './components/Layout'
import CustomCursor from './components/CustomCursor'
import Home from './pages/Home'

const Features = lazy(() => import('./pages/Features'))
const Product = lazy(() => import('./pages/Product'))
const Download = lazy(() => import('./pages/Download'))
const Documentation = lazy(() => import('./pages/Documentation'))
const Changelog = lazy(() => import('./pages/Changelog'))
const About = lazy(() => import('./pages/About'))

function PageLoader() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-cyan/30 border-t-cyan" />
    </div>
  )
}

export default function App() {
  const location = useLocation()

  return (
    <>
      <CustomCursor />
      <Layout>
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          >
            <Suspense fallback={<PageLoader />}>
              <Routes location={location}>
                <Route path="/" element={<Home />} />
                <Route path="/features" element={<Features />} />
                <Route path="/product" element={<Product />} />
                <Route path="/download" element={<Download />} />
                <Route path="/docs" element={<Documentation />} />
                <Route path="/changelog" element={<Changelog />} />
                <Route path="/about" element={<About />} />
                <Route path="*" element={<Home />} />
              </Routes>
            </Suspense>
          </motion.div>
        </AnimatePresence>
      </Layout>
    </>
  )
}
