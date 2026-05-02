import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, BarChart3, Search, TrendingUp, Lightbulb, Check, Loader2 } from 'lucide-react';


const AGENT_META = {
    'Market Researcher':  { icon: Search,     color: '#60a5fa', hint: 'Thu thập dữ liệu giá & tin tức thị trường'    },
    'Financial Analyst':  { icon: TrendingUp, color: '#a78bfa', hint: 'Tính RSI · MACD · ADX · Bollinger Bands'      },
    'Investment Advisor': { icon: Lightbulb,  color: '#34d399', hint: 'Chấm điểm tín hiệu & đưa ra khuyến nghị'      },
}

const DEFAULT_STEPS = Object.keys(AGENT_META).map(name => ({ name, status: 'pending', detail: '' }))

// ── Hook: phản ánh agentSteps trực tiếp vào display ─────────────────────────
// Animation sequence được điều khiển hoàn toàn từ useStockAnalysis.js
// Hook này chỉ cần trả về đúng data để render
function useDisplaySteps(agentSteps) {
    return agentSteps.length ? agentSteps : DEFAULT_STEPS
}

// ── AgentStep card ───────────────────────────────────────────────────────────
function AgentStep({ step, index }) {
    const meta      = AGENT_META[step.name] || {}
    const Icon      = meta.icon  || Search
    const color     = meta.color || '#60a5fa'
    const detail    = step.detail || meta.hint || ''
    const running   = step.status === 'running'
    const completed = step.status === 'completed'
    const failed    = step.status === 'failed'
    const pending   = step.status === 'pending'
    const accent    = failed ? '#ef4444' : color

    return (
        <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.08, duration: 0.3 }}
            style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '14px 16px', borderRadius: 14,
                border: `1px solid ${(running || completed) ? accent : 'rgba(255,255,255,0.07)'}`,
                background: running   ? `${accent}10`
                           : completed ? `${accent}08`
                           : failed    ? 'rgba(239,68,68,0.07)'
                           : 'rgba(255,255,255,0.02)',
                transition: 'border-color 0.5s ease, background 0.5s ease',
            }}
        >
            {/* Icon circle */}
            <div style={{ position: 'relative', flexShrink: 0 }}>
                <div style={{
                    width: 42, height: 42, borderRadius: '50%',
                    border: `2px solid ${pending ? 'rgba(255,255,255,0.1)' : accent}`,
                    background: pending ? 'rgba(255,255,255,0.04)' : `${accent}18`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    transition: 'all 0.5s ease',
                }}>
                    {completed && <Check size={18} color={accent} strokeWidth={2.5} />}
                    {running && (
                        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.1, ease: 'linear' }}>
                            <Loader2 size={18} color={accent} />
                        </motion.div>
                    )}
                    {failed  && <AlertCircle size={18} color="#ef4444" />}
                    {pending && <Icon size={18} color="rgba(255,255,255,0.2)" />}
                </div>

                {running && (
                    <motion.div
                        animate={{ scale: [1, 1.7], opacity: [0.5, 0] }}
                        transition={{ repeat: Infinity, duration: 1.6, ease: 'easeOut' }}
                        style={{ position: 'absolute', inset: -5, borderRadius: '50%', border: `1.5px solid ${accent}`, pointerEvents: 'none' }}
                    />
                )}
            </div>

            {/* Text */}
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                    fontSize: '0.9rem', fontWeight: 700, marginBottom: 3,
                    color: pending ? 'rgba(255,255,255,0.28)' : failed ? '#ef4444' : 'rgba(255,255,255,0.92)',
                    transition: 'color 0.4s',
                }}>
                    {step.name}
                </div>
                <div style={{ fontSize: '0.76rem', color: 'rgba(255,255,255,0.42)', lineHeight: 1.5 }}>
                    {running
                        ? <motion.span animate={{ opacity: [1, 0.4, 1] }} transition={{ repeat: Infinity, duration: 1.8 }}>{detail}</motion.span>
                        : <span>{detail}</span>
                    }
                </div>
            </div>

            {/* Badge */}
            <AnimatePresence mode="wait">
                {running && (
                    <motion.span key="r" initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                        style={{ flexShrink: 0, fontSize: '0.65rem', fontWeight: 800, letterSpacing: '0.5px', color: accent, background: `${accent}18`, border: `1px solid ${accent}40`, padding: '3px 9px', borderRadius: 6 }}>
                        ĐANG CHẠY
                    </motion.span>
                )}
                {completed && (
                    <motion.span key="c" initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }}
                        style={{ flexShrink: 0, fontSize: '0.65rem', fontWeight: 800, letterSpacing: '0.5px', color: accent, background: `${accent}18`, border: `1px solid ${accent}35`, padding: '3px 9px', borderRadius: 6 }}>
                        HOÀN TẤT
                    </motion.span>
                )}
                {failed && (
                    <motion.span key="f" initial={{ opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }}
                        style={{ flexShrink: 0, fontSize: '0.65rem', fontWeight: 800, color: '#ef4444', background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.35)', padding: '3px 9px', borderRadius: 6 }}>
                        LỖI
                    </motion.span>
                )}
            </AnimatePresence>
        </motion.div>
    )
}

// ── Progress bar ─────────────────────────────────────────────────────────────
function ProgressBar({ steps }) {
    const done = steps.filter(s => s.status === 'completed').length
    const pct  = steps.length ? Math.round((done / steps.length) * 100) : 0
    return (
        <div style={{ marginTop: 18 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: '0.67rem', color: 'rgba(255,255,255,0.3)', fontWeight: 600, letterSpacing: '1px', textTransform: 'uppercase' }}>Tiến độ</span>
                <span style={{ fontSize: '0.67rem', color: 'rgba(255,255,255,0.4)', fontWeight: 700 }}>{done}/{steps.length} agent</span>
            </div>
            <div style={{ height: 3, borderRadius: 99, background: 'rgba(255,255,255,0.07)', overflow: 'hidden' }}>
                <motion.div animate={{ width: `${pct}%` }} transition={{ duration: 0.6, ease: 'easeOut' }}
                    style={{ height: '100%', borderRadius: 99, background: 'linear-gradient(90deg,#60a5fa,#a78bfa,#34d399)' }} />
            </div>
        </div>
    )
}

// ── Main Loader ───────────────────────────────────────────────────────────────
const Loader = ({ loading, error, result, agentSteps = [] }) => {
    const displaySteps = useDisplaySteps(agentSteps)

    return (
        <AnimatePresence mode="wait">
            {loading && (
                <motion.div key="loading" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                    className="glass-card" style={{ padding: '2rem' }}>
                    <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
                        <div style={{ width: 52, height: 52, borderRadius: '50%', background: 'rgba(96,165,250,0.12)', border: '1.5px solid rgba(96,165,250,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem' }}>
                            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2.5, ease: 'linear' }}>
                                <Loader2 size={26} color="#60a5fa" />
                            </motion.div>
                        </div>
                        <h3 style={{ margin: '0 0 0.3rem', fontSize: '1.05rem', fontWeight: 700 }}>Đang điều phối tác nhân AI</h3>
                        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.8rem' }}>Các agent chạy tuần tự · tự động cập nhật</p>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {displaySteps.map((step, i) => <AgentStep key={step.name} step={step} index={i} />)}
                    </div>
                    <ProgressBar steps={displaySteps} />
                </motion.div>
            )}

            {error && (
                <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    className="glass-card" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <AlertCircle size={32} />
                        <p style={{ margin: 0 }}>{error}</p>
                    </div>
                </motion.div>
            )}

            {!result && !loading && !error && (
                <div className="glass-card loading-area" style={{ borderStyle: 'dashed', background: 'transparent' }}>
                    <BarChart3 size={64} color="var(--surface-lighter)" />
                    <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem', marginTop: '1rem' }}>
                        Hệ thống sẵn sàng. Vui lòng nhập mã cổ phiếu để bắt đầu quy trình AI.
                    </p>
                </div>
            )}
        </AnimatePresence>
    )
}

export default Loader;
