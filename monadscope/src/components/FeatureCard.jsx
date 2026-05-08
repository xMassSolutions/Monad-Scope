import { motion } from 'motion/react'

export default function FeatureCard({ title, description, icon: Icon, gradient, delay }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: 'easeOut', delay }}
      className="relative flex flex-col justify-start items-start w-full max-w-[260px] md:max-w-[300px] group mx-auto"
    >
      {/* Glow background */}
      <div
        className="absolute inset-0 w-full h-[260px] md:h-[300px] opacity-60 rounded-[40px] pointer-events-none"
        style={{
          background: gradient,
          filter: 'blur(45px)',
        }}
      />

      {/* Foreground card with gradient border */}
      <div
        className="relative self-stretch h-[260px] md:h-[300px] rounded-[40px] z-10 overflow-hidden"
        style={{
          border: '1px solid transparent',
          background: `linear-gradient(#1A1A1C, #1A1A1C) padding-box, ${gradient} border-box`,
        }}
      >
        <div className="w-full h-full p-7 flex flex-col justify-between">
          <div className="text-white/90">
            <Icon size={32} strokeWidth={2.5} />
          </div>
          <div>
            <h3 className="text-white font-medium text-xl mb-3 tracking-tight">{title}</h3>
            <p className="text-gray-400 text-[14px] leading-[1.6] font-normal selection:bg-white/20">
              {description}
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
