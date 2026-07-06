import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

export default function Modal({ open, onClose, title, children, maxWidth = "max-w-lg", testId }) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-start sm:items-center justify-center p-4 overflow-y-auto"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          data-testid={testId}
        >
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.97 }}
            transition={{ type: "spring", stiffness: 300, damping: 28 }}
            className={`relative w-full ${maxWidth} my-8 rounded-2xl bg-surface border border-elevated shadow-2xl`}
          >
            <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-elevated">
              <h3 className="font-heading text-xl font-bold text-white tracking-tight">{title}</h3>
              <button
                onClick={onClose}
                data-testid="modal-close"
                className="text-zinc-400 hover:text-white transition-colors rounded-full p-1 hover:bg-elevated"
              >
                <X size={20} />
              </button>
            </div>
            <div className="px-6 py-5">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function Field({ label, children }) {
  return (
    <label className="block mb-4">
      <span className="text-xs font-bold uppercase tracking-[0.15em] text-zinc-400">{label}</span>
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

export const inputCls =
  "w-full bg-void border border-elevated rounded-lg px-3.5 py-2.5 text-white placeholder-zinc-600 focus:border-volt focus:outline-none focus:ring-1 focus:ring-volt/40 transition-colors";

export const btnPrimary =
  "w-full bg-volt text-void font-bold rounded-lg py-3 hover:bg-volt-hover active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed";
