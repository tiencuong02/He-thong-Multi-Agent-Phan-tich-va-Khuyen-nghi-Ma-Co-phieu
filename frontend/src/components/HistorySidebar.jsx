import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Clock, TrendingUp, TrendingDown, Minus,
    Target, ShieldAlert, Activity, Zap, BarChart2
} from 'lucide-react';

// ── colour helpers ──────────────────────────────────────────────
const REC_COLOR = {
    BUY:  { text: '#10b981', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.35)', glow: 'rgba(16,185,129,0.25)' },
    SELL: { text: '#ef4444', bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.35)',  glow: 'rgba(239,68,68,0.25)'  },
    HOLD: { text: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.35)', glow: 'rgba(245,158,11,0.25)' },
};

const recKey   = (r = '') => r.toUpperCase().includes('BUY') ? 'BUY' : r.toUpperCase().includes('SELL') ? 'SELL' : 'HOLD';
const scoreCol = (s)      => s >= 4 ? '#10b981' : s <= -4 ? '#ef4444' : '#f59e0b';
const muted    = 'rgba(255,255,255,0.35)';
const cardBg   = 'rgba(255,255,255,0.04)';
const border   = 'rgba(255,255,255,0.08)';

// ── mini bar ────────────────────────────────────────────────────
function MiniBar({ value, max = 100, color }) {
    const pct = Math.min(Math.max((value / max) * 100, 0), 100);
    return (
        <div style={{ background: 'rgba(255,255,255,0.08)', borderRadius: 999, height: 4, overflow: 'hidden' }}>
            <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 1, ease: [0.25, 0.46, 0.45, 0.94] }}
                style={{ height: '100%', borderRadius: 999, background: color, boxShadow: `0 0 6px ${color}88` }}
            />
        </div>
    );
}

// ── metric row ──────────────────────────────────────────────────
function MetricRow({ icon: Icon, label, value, color }) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '5px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Icon size={11} color={muted} />
                <span style={{ fontSize: '0.7rem', color: muted }}>{label}</span>
            </div>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: color || 'rgba(255,255,255,0.8)' }}>
                {value}
            </span>
        </div>
    );
}

// ── quick indicator dot ─────────────────────────────────────────
function IndicatorDot({ label, value, color }) {
    return (
        <div style={{ textAlign: 'center', flex: 1 }}>
            <div style={{
                width: 8, height: 8, borderRadius: '50%',
                background: color, margin: '0 auto 4px',
                boxShadow: `0 0 6px ${color}`,
            }} />
            <div style={{ fontSize: '0.62rem', color: muted, marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color }}>{value}</div>
        </div>
    );
}

// ── main summary card ───────────────────────────────────────────
function QuickSummaryCard({ result }) {
    const rec     = recKey(result.recommendation);
    const c       = REC_COLOR[rec];
    const sc      = result.score ?? 0;
    const scColor = scoreCol(sc);

    // RSI colour
    const rsiColor = result.rsi > 70 ? '#ef4444' : result.rsi < 30 ? '#10b981' : '#f59e0b';
    // MACD colour
    const macdColor = (result.macd_histogram ?? 0) > 0 ? '#10b981' : '#ef4444';
    // confidence %
    const confPct = Math.round((result.confidence ?? 0) * 100);

    return (
        <motion.div
            key={result.ticker}
            initial={{ opacity: 0, y: -12, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.35 }}
            style={{
                background: cardBg,
                border: `1px solid ${c.border}`,
                borderRadius: 16,
                padding: '16px',
                marginBottom: 16,
                boxShadow: `0 0 24px ${c.glow}`,
                backdropFilter: 'blur(8px)',
            }}
        >
            {/* Header: ticker + badge */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                    <div style={{ fontSize: '1.35rem', fontWeight: 900, letterSpacing: '-0.5px', color: '#fff' }}>
                        {result.ticker}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: muted, marginTop: 1 }}>
                        {result.price ? `$${result.price.toLocaleString()}` : '—'}
                    </div>
                </div>
                <motion.div
                    animate={{ boxShadow: [`0 0 8px ${c.glow}`, `0 0 18px ${c.glow}`, `0 0 8px ${c.glow}`] }}
                    transition={{ repeat: Infinity, duration: 2.5 }}
                    style={{
                        background: c.bg,
                        border: `1px solid ${c.border}`,
                        color: c.text,
                        borderRadius: 8,
                        padding: '4px 12px',
                        fontSize: '0.8rem',
                        fontWeight: 900,
                        letterSpacing: '1px',
                    }}
                >
                    {result.recommendation}
                </motion.div>
            </div>

            {/* Score bar */}
            <div style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                    <span style={{ fontSize: '0.65rem', color: muted, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase' }}>
                        Điểm kỹ thuật
                    </span>
                    <span style={{ fontSize: '0.75rem', fontWeight: 800, color: scColor }}>
                        {sc > 0 ? '+' : ''}{sc} / 10
                    </span>
                </div>
                <MiniBar value={sc + 10} max={20} color={scColor} />
            </div>

            {/* Divider */}
            <div style={{ height: 1, background: border, marginBottom: 10 }} />

            {/* Key metrics */}
            <div style={{ marginBottom: 12 }}>
                {result.target_price && (
                    <MetricRow
                        icon={Target}
                        label="Mục tiêu"
                        value={`$${result.target_price.toLocaleString()}`}
                        color="#10b981"
                    />
                )}
                {result.stop_loss && (
                    <MetricRow
                        icon={ShieldAlert}
                        label="Cắt lỗ"
                        value={`$${result.stop_loss.toLocaleString()}`}
                        color="#ef4444"
                    />
                )}
                <MetricRow
                    icon={Activity}
                    label="Độ tin cậy"
                    value={`${confPct}%`}
                    color={confPct >= 60 ? '#10b981' : confPct >= 40 ? '#f59e0b' : '#ef4444'}
                />
            </div>

            {/* Confidence bar */}
            <MiniBar
                value={confPct}
                max={100}
                color={confPct >= 60 ? '#10b981' : confPct >= 40 ? '#f59e0b' : '#ef4444'}
            />

            {/* Indicator dots */}
            {(result.rsi != null || result.macd_histogram != null || result.adx != null) && (
                <>
                    <div style={{ height: 1, background: border, margin: '12px 0' }} />
                    <div style={{ display: 'flex', justifyContent: 'space-around' }}>
                        {result.rsi != null && (
                            <IndicatorDot label="RSI" value={result.rsi.toFixed(0)} color={rsiColor} />
                        )}
                        {result.macd_histogram != null && (
                            <IndicatorDot
                                label="MACD"
                                value={(result.macd_histogram > 0 ? '+' : '') + result.macd_histogram.toFixed(2)}
                                color={macdColor}
                            />
                        )}
                        {result.adx != null && (
                            <IndicatorDot
                                label="ADX"
                                value={result.adx.toFixed(0)}
                                color={result.adx < 20 ? muted : result.adx < 40 ? '#f59e0b' : '#10b981'}
                            />
                        )}
                    </div>
                </>
            )}
        </motion.div>
    );
}

// ── main sidebar ────────────────────────────────────────────────
const HistorySidebar = ({ history, result, onResultClick }) => {
    return (
        <aside className="sidebar-sticky fade-in" style={{ animationDelay: '0.2s' }}>

            {/* Summary card */}
            <AnimatePresence mode="wait">
                {result && <QuickSummaryCard key={result.ticker + result.price} result={result} />}
            </AnimatePresence>

            {/* History */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                <Clock size={14} color={muted} />
                <span style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: muted }}>
                    Lịch sử gần đây
                </span>
            </div>

            <div className="history-list">
                {history.slice(0, 10).map((item, idx) => (
                    <motion.div
                        whileHover={{ scale: 1.02 }}
                        key={idx}
                        className="history-item"
                        onClick={() => onResultClick(item)}
                    >
                        <div>
                            <div style={{ fontWeight: 800, fontSize: '1rem' }}>{item.ticker}</div>
                            <div style={{ fontSize: '0.72rem', color: muted }}>
                                {new Date(item.created_at).toLocaleDateString('vi-VN')}
                            </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                            {item.trend === 'up'     && <TrendingUp   size={14} color="#10b981" />}
                            {item.trend === 'down'   && <TrendingDown size={14} color="#ef4444" />}
                            {item.trend === 'stable' && <Minus        size={14} color="#f59e0b" />}
                            <div className={
                                item.recommendation.toUpperCase().includes('BUY')  ? 'rec-buy'  :
                                item.recommendation.toUpperCase().includes('SELL') ? 'rec-sell' : 'rec-hold'
                            }>
                                {item.recommendation}
                            </div>
                        </div>
                    </motion.div>
                ))}
                {history.length === 0 && (
                    <p style={{ textAlign: 'center', color: muted, fontStyle: 'italic', fontSize: '0.82rem' }}>
                        Chưa có dữ liệu.
                    </p>
                )}
            </div>
        </aside>
    );
};

export default HistorySidebar;
