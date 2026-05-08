import { Monitor, Palette, Zap } from 'lucide-react'
import { motion } from 'motion/react'
import FeatureCard from './FeatureCard'

const cards = [
  {
    title: 'Hardware',
    description: 'My entire desktop setup is built for power. It is silent, durable, and holds my focus.',
    icon: Monitor,
    gradient: 'linear-gradient(137deg, #FF3D77 0%, #FFB1CE 45%, #FF9D3C 100%)',
    delay: 0.1,
  },
  {
    title: 'Studio',
    description: 'Studio is where I define every single pixel. It is the hub for each canvas I deliver.',
    icon: Palette,
    gradient: 'linear-gradient(137deg, #FFFFFF 0%, #7DD3FC 45%, #06B6D4 100%)',
    delay: 0.2,
  },
  {
    title: 'Motion',
    description: 'I use Motion to build lively prototypes, bridging the gap between views and code.',
    icon: Zap,
    gradient: 'linear-gradient(137deg, #4361EE 0%, #E0AEFF 45%, #F72585 100%)',
    delay: 0.3,
  },
]

export default function FeaturesSection() {
  return (
    <section id="features" className="w-full bg-[#0A0A0B] py-24 px-6 md:px-12 scroll-mt-16">
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
          Everything you need
        </h2>
        <p className="text-white/40 text-base max-w-md mx-auto">
          Purpose-built tools for deep contract intelligence on Monad.
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
