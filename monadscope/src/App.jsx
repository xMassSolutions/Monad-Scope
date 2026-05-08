import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import HeroSection from './components/HeroSection'
import FeaturesSection from './components/FeaturesSection'
import DashboardPreview from './components/DashboardPreview'
import Footer from './components/Footer'

const AppShell = lazy(() => import('./components/AppShell'))
const ContractIntelligence = lazy(() => import('./pages/ContractIntelligence'))
const Library = lazy(() => import('./pages/Library'))
const Projects = lazy(() => import('./pages/Projects'))
const Exploits = lazy(() => import('./pages/Exploits'))

function Landing() {
  return (
    <div className="relative min-h-screen bg-[#0A0A0B]">
      {/* Page-wide fluid backdrop — animates the same AVIF behind every section */}
      <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <img
          src="/background.avif"
          alt=""
          aria-hidden
          decoding="async"
          className="bg-fluid absolute inset-0 w-full h-full object-cover opacity-40"
          style={{ animationDuration: '40s' }}
        />
        {/* Soft radial wash so headlines + cards stay legible without killing the colors */}
        <div
          className="absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse at center, rgba(10,10,11,0.25) 0%, rgba(10,10,11,0.55) 70%, rgba(10,10,11,0.8) 100%)',
          }}
        />
      </div>
      <div className="relative z-10">
        <HeroSection />
        <FeaturesSection />
        <DashboardPreview />
        <Footer />
      </div>
    </div>
  )
}

function AppFallback() {
  return (
    <div className="min-h-screen w-full bg-[#0A0A0B] flex items-center justify-center">
      <div className="w-6 h-6 rounded-full border-2 border-white/15 border-t-white/60 animate-spin" />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<AppFallback />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/app" element={<AppShell />}>
            <Route index element={<ContractIntelligence />} />
            <Route path="contract/:address" element={<ContractIntelligence />} />
            <Route path="library/recent" element={<Library kind="recent" />} />
            <Route path="library/high-risk" element={<Library kind="high-risk" />} />
            <Route path="projects" element={<Projects />} />
            <Route path="projects/:projectId" element={<Projects />} />
            <Route path="exploits" element={<Exploits />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
