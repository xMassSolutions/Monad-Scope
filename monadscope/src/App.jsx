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

function Landing() {
  return (
    <div className="relative min-h-screen bg-[#0A0A0B]">
      {/* Page-wide static backdrop behind lower sections — no animation here, hero carries the motion */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-0 overflow-hidden opacity-25"
        style={{
          maskImage:
            'linear-gradient(to bottom, transparent 0%, transparent 60%, rgba(0,0,0,0.6) 80%, rgba(0,0,0,0.3) 100%)',
          WebkitMaskImage:
            'linear-gradient(to bottom, transparent 0%, transparent 60%, rgba(0,0,0,0.6) 80%, rgba(0,0,0,0.3) 100%)',
        }}
      >
        <img
          src="/background.avif"
          alt=""
          aria-hidden
          decoding="async"
          loading="lazy"
          className="absolute inset-0 w-full h-full object-cover"
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
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
