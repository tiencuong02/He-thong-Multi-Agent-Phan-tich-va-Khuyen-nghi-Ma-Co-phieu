import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Activity, BarChart2, Zap, Minus } from 'lucide-react'

const C = {
  positive: '#10b981',
  negative: '#ef4444',
  neutral:  '#f59e0b',
  blue:     '#60a5fa',
  muted:    'rgba(255,255,255,0.35)',
  cardBg:   'rgba(255,255,255,0.04)',
  border:   'rgba(255,255,255,0.08)',
}

function ProgressBar({ value, max = 100, color }) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100)
  return (
    <div style={{ background: 'rgba(255,255,255,0.08)', borderRadius: 999, height: 5, overflow: 'hidden' }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 1.1, ease: [0.25, 0.46, 0.45, 0.94] }}
        style={{ height: '100%', borderRadius: 999, background: color, boxShadow: `0 0 6px ${color}88` }}
      />
    </div>
  )
}

function Card({ icon: Icon, title, delay, children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
      style={{ background: C.cardBg, border: `1px solid ${C.border}`, borderRadius: 12, padding: '14px 16px' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
        <Icon size={12} color={C.muted} />
        <span style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.muted }}>
          {title}
        </span>
      </div>
      {children}
    </motion.div>
  )
}

function BigValue({ value, label, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
      <span style={{ fontSize: '1.55rem', fontWeight: 700, color, lineHeight: 1 }}>{value}</span>
      <span style={{ fontSize: '0.7rem', fontWeight: 600, color }}>{label}</span>
    </div>
  )
}

function SignalRow({ text, index }) {
  const isPositive = text.includes('(+')
  const color = isPositive ? C.positive : C.neutral
  const clean = text.replace(/\(\+\d+\)|\(-\d+\)/g, '').trim()
  const score = text.match(/\(([+-]\d+)\)/)?.[1]
  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.55 + index * 0.07 }}
      style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '5px 0', borderBottom: `1px solid ${C.border}` }}
    >
      <div style={{
        flexShrink: 0, marginTop: 2,
        width: 16, height: 16, borderRadius: 4,
        background: `${color}20`, border: `1px solid ${color}55`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: '0.55rem', fontWeight: 900, color }}>{isPositive ? '▲' : '!'}</span>
      </div>
      <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.72)', lineHeight: 1.5, flex: 1 }}>{clean}</span>
      {score && (
        <span style={{ flexShrink: 0, fontSize: '0.7rem', fontWeight: 700, color, background: `${color}15`, padding: '1px 6px', borderRadius: 4 }}>
          {score}
        </span>
      )}
    </motion.div>
  )
}

export default function TechnicalDashboard({ result }) {
  const {
    rsi, macd_histogram, adx, plus_di, minus_di,
    bb_upper, bb_lower, atr, volume_change, score, signals,
  } = result

  const rsiColor  = rsi > 70 ? C.negative : rsi < 30 ? C.positive : C.neutral
  const rsiLabel  = rsi > 70 ? 'Mua quá mức' : rsi < 30 ? 'Bán quá mức' : 'Trung lập'

  const macdUp    = (macd_histogram ?? 0) > 0
  const macdColor = macdUp ? C.positive : C.negative

  const adxColor  = adx < 20 ? C.muted : adx < 25 ? C.neutral : adx < 40 ? C.positive : C.blue
  const adxLabel  = adx < 20 ? 'Sideway' : adx < 25 ? 'Hình thành' : adx < 40 ? 'Rõ ràng' : 'Rất mạnh'

  const volPct    = Math.abs((volume_change ?? 0) * 100)
  const volUp     = (volume_change ?? 0) >= 0
  const volColor  = volUp ? C.positive : C.negative

  const scoreColor = score >= 4 ? C.positive : score <= -4 ? C.negative : C.neutral
  const scoreLabel = score >= 4 ? 'Tích cực' : score <= -4 ? 'Tiêu cực' : 'Trung lập'

  return (
    <div style={{ fontFamily: 'inherit' }}>

      {/* Quick summary */}
      <motion.div
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          background: `${scoreColor}12`,
          border: `1px solid ${scoreColor}45`,
          borderRadius: 10,
          padding: '10px 14px',
          marginBottom: 14,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <motion.div
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ repeat: Infinity, duration: 2 }}
          style={{ width: 7, height: 7, borderRadius: '50%', background: scoreColor, flexShrink: 0 }}
        />
        <span style={{ fontSize: '0.83rem', color: 'rgba(255,255,255,0.82)' }}>
          Tín hiệu tổng hợp{' '}
          <strong style={{ color: scoreColor }}>{scoreLabel}</strong>
          {score !== undefined && (
            <> — Điểm kỹ thuật{' '}
              <strong style={{ color: scoreColor }}>{score > 0 ? '+' : ''}{score}/10</strong>
            </>
          )}
        </span>
      </motion.div>

      {/* 2-column grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>

        {/* RSI */}
        {rsi != null && (
          <Card icon={Activity} title="Sức mua / bán" delay={0.08}>
            <BigValue value={rsi.toFixed(1)} label={rsiLabel} color={rsiColor} />
            <ProgressBar value={rsi} max={100} color={rsiColor} />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
              <span style={{ fontSize: '0.6rem', color: C.muted }}>0</span>
              <span style={{ fontSize: '0.6rem', color: C.muted }}>50</span>
              <span style={{ fontSize: '0.6rem', color: C.muted }}>100</span>
            </div>
          </Card>
        )}

        {/* ADX */}
        {adx != null && (
          <Card icon={TrendingUp} title="Độ mạnh xu hướng" delay={0.14}>
            <BigValue value={adx.toFixed(1)} label={adxLabel} color={adxColor} />
            <ProgressBar value={adx} max={60} color={adxColor} />
            {plus_di != null && minus_di != null && (
              <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                <div style={{ flex: 1, background: `${C.positive}12`, border: `1px solid ${C.positive}30`, borderRadius: 6, padding: '4px 0', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.58rem', color: C.muted }}>Lực tăng</div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 700, color: C.positive }}>{plus_di.toFixed(1)}</div>
                </div>
                <div style={{ flex: 1, background: `${C.negative}12`, border: `1px solid ${C.negative}30`, borderRadius: 6, padding: '4px 0', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.58rem', color: C.muted }}>Lực giảm</div>
                  <div style={{ fontSize: '0.88rem', fontWeight: 700, color: C.negative }}>{minus_di.toFixed(1)}</div>
                </div>
              </div>
            )}
          </Card>
        )}

        {/* MACD */}
        {macd_histogram != null && (
          <Card icon={Zap} title="Động lượng MACD" delay={0.2}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '1.55rem', fontWeight: 700, color: macdColor, lineHeight: 1 }}>
                  {macd_histogram > 0 ? '+' : ''}{macd_histogram.toFixed(2)}
                </div>
                <div style={{ fontSize: '0.7rem', fontWeight: 600, color: macdColor, marginTop: 3 }}>
                  {macdUp ? 'Đà tăng' : 'Đà giảm'}
                </div>
              </div>
              <div style={{
                width: 38, height: 38, borderRadius: '50%',
                background: `${macdColor}18`, border: `2px solid ${macdColor}50`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {macdUp
                  ? <TrendingUp size={16} color={macdColor} />
                  : <TrendingDown size={16} color={macdColor} />
                }
              </div>
            </div>
          </Card>
        )}

        {/* Volume */}
        <Card icon={BarChart2} title="Khối lượng" delay={0.26}>
          <BigValue
            value={`${volUp ? '+' : '-'}${volPct.toFixed(1)}%`}
            label={volUp ? 'Cao hơn TB' : 'Thấp hơn TB'}
            color={volColor}
          />
          <ProgressBar value={Math.min(volPct, 100)} max={100} color={volColor} />
          <div style={{ fontSize: '0.6rem', color: C.muted, marginTop: 4 }}>so với trung bình 5 phiên</div>
        </Card>
      </div>

      {/* Bollinger bands + ATR */}
      {bb_upper != null && bb_lower != null && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.32 }}
          style={{
            background: C.cardBg, border: `1px solid ${C.border}`,
            borderRadius: 12, padding: '12px 16px', marginBottom: 10,
            display: 'flex', alignItems: 'center', gap: 12,
          }}
        >
          <Minus size={12} color={C.muted} style={{ flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.muted, marginBottom: 7 }}>
              Vùng dao động giá (Bollinger)
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '0.88rem', fontWeight: 600, color: C.negative }}>{bb_lower.toFixed(2)}</span>
              <div style={{ flex: 1, height: 4, borderRadius: 999, background: `linear-gradient(90deg, ${C.negative}55, ${C.neutral}55, ${C.positive}55)` }} />
              <span style={{ fontSize: '0.88rem', fontWeight: 600, color: C.positive }}>{bb_upper.toFixed(2)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3 }}>
              <span style={{ fontSize: '0.6rem', color: C.muted }}>Đáy hỗ trợ</span>
              <span style={{ fontSize: '0.6rem', color: C.muted }}>Đỉnh kháng cự</span>
            </div>
          </div>
          {atr != null && (
            <div style={{ borderLeft: `1px solid ${C.border}`, paddingLeft: 12, textAlign: 'center', flexShrink: 0 }}>
              <div style={{ fontSize: '0.6rem', color: C.muted }}>Biến động</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'rgba(255,255,255,0.65)' }}>±{atr.toFixed(2)}</div>
              <div style={{ fontSize: '0.6rem', color: C.muted }}>/phiên</div>
            </div>
          )}
        </motion.div>
      )}

      {/* Signals */}
      {signals && signals.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.45 }}
          style={{ background: C.cardBg, border: `1px solid ${C.border}`, borderRadius: 12, padding: '14px 16px' }}
        >
          <div style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', color: C.muted, marginBottom: 8 }}>
            Tín hiệu phân tích
          </div>
          <div>
            {signals.map((s, i) => <SignalRow key={i} text={s} index={i} />)}
          </div>
        </motion.div>
      )}
    </div>
  )
}
