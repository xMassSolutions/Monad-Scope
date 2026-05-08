import { motion } from 'motion/react'

export default function Footer() {
  return (
    <footer className="w-full border-t border-white/8 bg-[#0A0A0B] py-12 px-6 md:px-12">
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
        className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6"
      >
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="MonadScope" decoding="async" loading="lazy" className="w-7 h-7 object-contain" />
          <span className="text-white/50 text-sm font-medium">MonadScope</span>
        </div>
        <p className="text-white/20 text-xs">© 2026 MonadScope</p>
      </motion.div>
    </footer>
  )
}
