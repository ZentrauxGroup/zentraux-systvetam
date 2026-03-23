/**
 * SYSTVETAM — Task Create Modal
 * Zentraux Group LLC
 *
 * Framer Motion modal — slides up from bottom, dark glass overlay.
 * Submits via useCreateTask() → POST /api/tasks.
 * On success: close + gold toast with ZG-ref. On error: inline message.
 */

import { useState, useCallback, useEffect, type FormEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Plus, Check } from 'lucide-react';
import { useCreateTask } from '@/api/tasks';

// ---------------------------------------------------------------------------
// Options — from directive enums
// ---------------------------------------------------------------------------

const TASK_TYPES = [
  'STANDARD', 'INTELLIGENCE_BRIEF', 'BUILD_FROM_INTEL',
  'OPPORTUNITY', 'GTM_CAMPAIGN', 'VOICE_OUTREACH',
  'SECURITY_REVIEW', 'QA_EVALUATION',
] as const;

const DEPARTMENTS = [
  'ENGINEERING', 'GTM', 'INTELLIGENCE', 'STRATEGY',
  'FINANCE', 'DELIVERY', 'GOVERNANCE',
] as const;

const PRIORITIES = [
  { value: 1, label: 'CRITICAL' },
  { value: 2, label: 'HIGH' },
  { value: 3, label: 'NORMAL' },
  { value: 4, label: 'LOW' },
  { value: 5, label: 'BACKLOG' },
] as const;

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------

function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000);
    return () => clearTimeout(t);
  }, [onDismiss]);

  return (
    <motion.div
      initial={{ opacity: 0, y: -10, x: 10 }}
      animate={{ opacity: 1, y: 0, x: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="
        fixed top-4 right-4 z-[60]
        flex items-center gap-2 px-4 py-2.5 rounded-circuit
        bg-obsidian-elevated border border-gold/30
        shadow-gold-glow
      "
    >
      <Check className="w-3.5 h-3.5 text-gold" />
      <span className="text-xs font-mono text-gold">{message}</span>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

interface TaskCreateModalProps {
  open: boolean;
  onClose: () => void;
}

export function TaskCreateModal({ open, onClose }: TaskCreateModalProps) {
  const createTask = useCreateTask();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [taskType, setTaskType] = useState('STANDARD');
  const [priority, setPriority] = useState(3);
  const [department, setDepartment] = useState('ENGINEERING');
  const [plane, setPlane] = useState<'cloud' | 'local'>('cloud');
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const resetForm = useCallback(() => {
    setTitle('');
    setDescription('');
    setTaskType('STANDARD');
    setPriority(3);
    setDepartment('ENGINEERING');
    setPlane('cloud');
    setError(null);
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setError(null);

    try {
      const result = await createTask.mutateAsync({
        title: title.trim(),
        description: description.trim() || undefined,
        task_type: taskType,
        priority,
        department,
        source: 'TOWER_DASHBOARD',
      });
      resetForm();
      onClose();
      setToast(`${result.task_ref} created`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create task.';
      setError(msg);
    }
  };

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  return (
    <>
      {/* Toast */}
      <AnimatePresence>
        {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
      </AnimatePresence>

      {/* Modal */}
      <AnimatePresence>
        {open && (
          <>
            {/* Overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs"
            />

            {/* Panel */}
            <motion.div
              initial={{ opacity: 0, y: 100 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 100 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="
                fixed bottom-0 left-0 right-0 z-50
                max-h-[85vh] overflow-y-auto
                bg-obsidian-panel border-t border-glass-border
                rounded-t-2xl p-5
                md:max-w-lg md:mx-auto md:bottom-8 md:rounded-2xl md:border
              "
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <Plus className="w-4 h-4 text-gold" />
                  <h2 className="text-sm font-mono font-semibold tracking-wider text-gold">
                    NEW TASK
                  </h2>
                </div>
                <button onClick={onClose} className="text-glass-muted hover:text-glass-text transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Form */}
              <div className="space-y-4">
                {/* Title */}
                <Field label="TITLE" required>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="What needs to be done"
                    className="field-input"
                    autoFocus
                  />
                </Field>

                {/* Description */}
                <Field label="DESCRIPTION">
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Details, context, requirements..."
                    rows={3}
                    className="field-input resize-none"
                  />
                </Field>

                {/* Type + Priority row */}
                <div className="grid grid-cols-2 gap-3">
                  <Field label="TYPE">
                    <select
                      value={taskType}
                      onChange={(e) => setTaskType(e.target.value)}
                      className="field-input"
                    >
                      {TASK_TYPES.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </Field>

                  <Field label="PRIORITY">
                    <select
                      value={priority}
                      onChange={(e) => setPriority(Number(e.target.value))}
                      className="field-input"
                    >
                      {PRIORITIES.map((p) => (
                        <option key={p.value} value={p.value}>{p.label}</option>
                      ))}
                    </select>
                  </Field>
                </div>

                {/* Department + Plane row */}
                <div className="grid grid-cols-2 gap-3">
                  <Field label="DEPARTMENT">
                    <select
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      className="field-input"
                    >
                      {DEPARTMENTS.map((d) => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                  </Field>

                  <Field label="EXECUTION PLANE">
                    <div className="flex rounded-circuit overflow-hidden border border-glass-border">
                      <button
                        type="button"
                        onClick={() => setPlane('cloud')}
                        className={`
                          flex-1 py-2 text-xxs font-mono tracking-wider transition-colors
                          ${plane === 'cloud'
                            ? 'bg-gold/15 text-gold border-r border-gold/20'
                            : 'bg-glass text-glass-muted border-r border-glass-border hover:bg-glass-hover'
                          }
                        `}
                      >
                        CLOUD
                      </button>
                      <button
                        type="button"
                        onClick={() => setPlane('local')}
                        className={`
                          flex-1 py-2 text-xxs font-mono tracking-wider transition-colors
                          ${plane === 'local'
                            ? 'bg-gold/15 text-gold'
                            : 'bg-glass text-glass-muted hover:bg-glass-hover'
                          }
                        `}
                      >
                        LOCAL
                      </button>
                    </div>
                  </Field>
                </div>

                {/* Error */}
                {error && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-xs font-mono text-status-error"
                  >
                    {error}
                  </motion.p>
                )}

                {/* Submit */}
                <button
                  onClick={handleSubmit}
                  disabled={!title.trim() || createTask.isPending}
                  className="
                    w-full flex items-center justify-center gap-2
                    px-4 py-2.5 rounded-circuit
                    bg-gold/10 border border-gold/30 text-gold
                    hover:bg-gold/20 hover:border-gold/50
                    disabled:opacity-30 disabled:cursor-not-allowed
                    transition-all duration-200
                    font-mono text-sm tracking-wider
                  "
                >
                  <Plus className="w-4 h-4" />
                  {createTask.isPending ? 'CREATING...' : 'CREATE TASK'}
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

// ---------------------------------------------------------------------------
// Field wrapper
// ---------------------------------------------------------------------------

function Field({ label, required, children }: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xxs font-mono text-glass-muted mb-1.5 tracking-wider">
        {label}{required && <span className="text-status-error ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}
