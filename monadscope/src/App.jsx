import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import HeroSection from './components/HeroSection'
import FeaturesSection from './components/FeaturesSection'
import DashboardPreview from './components/DashboardPreview'
import Footer from './components/Footer'
import AppShell from './components/AppShell'
import ContractIntelligence from './pages/ContractIntelligence'
import Library from './pages/Library'
import Projects from './pages/Projects'
import Exploits from './pages/Exploits'

function Landing() {
  return (
    <div className="relative min-h-screen bg-[#0A0A0B]">
      {/* Page-wide drifting backdrop behind lower sections */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-0 overflow-hidden opacity-30"
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
          className="bg-fluid absolute inset-0 w-full h-full object-cover"
          style={{ animationDuration: '40s, 13s' }}
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

export default function App() {
  return (
    <BrowserRouter>
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
    </BrowserRouter>
  )
}
