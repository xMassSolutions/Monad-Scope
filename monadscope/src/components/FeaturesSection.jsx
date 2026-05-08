import { Radio, ShieldCheck, Sparkles } from 'lucide-react'
import { motion } from 'motion/react'
import FeatureCard from './FeatureCard'

const cards = [
  {
    title: 'Real-time ingest',
    description:
      'Live WebSocket stream of Monad mainnet. Every newly deployed contract is detected at Voted-block finality — no reorgs, no waiting.',
    icon: Radio,
    gradient: 'linear-gradient(137deg, #FF3D77 0%, #FFB1CE 45%, #FF9D3C 100%)',
    delay: 0.1,
  },
  {
    title: 'Risk + confidence scoring',
    description:
      'Deterministic findings with weighted severity, classification, and a transparent risk tier. Every contract gets a clear escalate / monitor / allow recommendation.',
    icon: ShieldCheck,
    gradient: 'linear-gradient(137deg, #FFFFFF 0%, #7DD3FC 45%, #06B6D4 100%)',
    delay: 0.2,
  },
  {
    title: 'Prime deep analysis',
    description:
      'An optional paid layer powered by Fortytwo Prime. Goes beyond static rules to reason about the hardest contracts when free signals alone are not enough.',
    icon: Sparkles,
    gradient: 'linear-gradient(137deg, #4361EE 0%, #E0AEFF 45%, #F72585 100%)',
    delay: 0.3,
  },
]

export default function FeaturesSection() {
  return (
    <section id="features" className="w-full py-24 px-6 md:px-12 scroll-mt-16">
      {/* Section header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
        className="text-center mb-16"
      >
        <span className="inline-block px-3 py-1 mb-4 text-xs font-medium tracking-widest uppercase text-white/40 border border-white/10 rounded-full">
          Features
        </span>
        <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight mb-4">
          Built for the speed of Monad
        </h2>
        <p className="text-white/40 text-base max-w-md mx-auto">
          Streaming ingest, transparent scoring, and an optional reasoning layer — purpose-built for a parallel-EVM chain.
        </p>
      </motion.div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-3 lg:gap-3 w-full max-w-[936px] mx-auto">
        {cards.map((card) => (
          <FeatureCard key={card.title} {...card} />
        ))}
      </div>
    </section>
  )
}
