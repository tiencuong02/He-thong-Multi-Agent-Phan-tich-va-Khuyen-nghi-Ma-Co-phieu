import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Clock, BarChart3, TrendingUp, TrendingDown, Globe, Search, Zap, Newspaper } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import ReactMarkdown from 'react-markdown';
import TechnicalDashboard from './TechnicalDashboard';

const getBadgeClass = (rec) => {
    const r = rec.toUpperCase();
    if (r.includes('BUY')) return 'badge badge-buy';
    if (r.includes('SELL')) return 'badge badge-sell';
    return 'badge badge-hold';
};

const getAssessmentStyle = (assessment) => {
    if (assessment === 'Tích cực') return { background: 'rgba(34, 197, 94, 0.15)', color: '#22c55e', border: '1px solid rgba(34, 197, 94, 0.3)' };
    if (assessment === 'Tiêu cực') return { background: 'rgba(244, 63, 94, 0.15)', color: '#f43f5e', border: '1px solid rgba(244, 63, 94, 0.3)' };
    return { background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: '1px solid rgba(148, 163, 184, 0.3)' };
};

const getSentimentColor = (label) => {
    if (label === 'Tích cực') return '#22c55e';
    if (label === 'Tiêu cực') return '#f43f5e';
    return '#94a3b8';
};

const getAgentIcon = (agentName) => {
    const name = agentName.toLowerCase();
    if (name.includes('market')) return <Globe size={20} />;
    if (name.includes('financial')) return <BarChart3 size={20} />;
    if (name.includes('investment')) return <Zap size={20} />;
    return <Search size={20} />;
};

const AnalysisResult = ({ result }) => {
    if (!result) return null;

    const getTrendMeta = (trend) => {
        if (trend === 'up') return {
            cardClass: 'impact-opportunity',
            textClass: 'opportunity-text',
            label: 'TĂNG TRƯỞNG',
            icon: <TrendingUp size={20} />
        };
        if (trend === 'down') return {
            cardClass: 'impact-risk',
            textClass: 'risk-text',
            label: 'SUY GIẢM',
            icon: <TrendingDown size={20} />
        };
        return {
            cardClass: 'impact-hold',
            textClass: 'hold-text',
            label: 'ĐI NGANG',
            icon: <BarChart3 size={20} />
        };
    };

    const trendMeta = getTrendMeta(result.trend);
    const sentimentColor = getSentimentColor(result.sentiment_label);
    const sentimentScore = result.sentiment_score ?? null;
    const sentimentPct = sentimentScore !== null ? Math.round(((sentimentScore + 1) / 2) * 100) : null;

    const chartData = useMemo(() => {
        const prices = result.price_history;
        if (!prices || prices.length === 0) return [];
        // Use 80 days for MA calculation warmup, display only last 60
        const calcSlice = prices.slice(-80);
        const allPoints = calcSlice.map((p, i, arr) => {
            const close = parseFloat(p.close);
            const prev5 = arr.slice(Math.max(0, i - 4), i + 1);
            const prev20 = arr.slice(Math.max(0, i - 19), i + 1);
            const ma5 = prev5.length === 5 ? parseFloat((prev5.reduce((s, x) => s + parseFloat(x.close), 0) / 5).toFixed(2)) : null;
            const ma20 = prev20.length === 20 ? parseFloat((prev20.reduce((s, x) => s + parseFloat(x.close), 0) / 20).toFixed(2)) : null;
            const [, mm, dd] = p.date.split('-');
            return { date: `${dd}/${mm}`, close, ma5, ma20 };
        });
        return allPoints.slice(-60);
    }, [result.price_history]);

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card"
        >
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
                <div>
                    <h2 style={{ fontSize: '2.5rem', margin: 0 }}>{result.ticker}</h2>
                    <p style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Clock size={16} /> Cập nhật lúc {new Date(result.created_at).toLocaleTimeString()}
                    </p>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
                    <div 
                        className={getBadgeClass(result.recommendation)}
                        style={{ 
                            fontSize: '1.1rem', 
                            padding: '0.65rem 2rem', 
                            borderWidth: '1.5px'
                        }}
                    >
                        {result.recommendation.toUpperCase().includes('BUY') && <TrendingUp size={20} style={{ marginRight: '6px' }}/>}
                        {result.recommendation.toUpperCase().includes('SELL') && <TrendingDown size={20} style={{ marginRight: '6px' }}/>}
                        {result.recommendation.toUpperCase().includes('HOLD') && <BarChart3 size={20} style={{ marginRight: '6px' }}/>}
                        {result.recommendation}
                    </div>

                    {result.fallback_used && (
                        <span style={{ fontSize: '0.7rem', background: 'rgba(234, 179, 8, 0.1)', color: '#eab308', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(234, 179, 8, 0.2)' }}>
                            ⚠️ Dữ liệu mô phỏng
                        </span>
                    )}
                </div>
            </div>

            {/* Metric Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                <div className="impact-card" style={{ background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.1)' }}>
                    <div style={{ color: '#38bdf8', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem' }}>GIÁ MỤC TIÊU</div>
                    <div style={{ fontSize: '1.8rem', fontWeight: 700 }}>{result.target_price?.toLocaleString()}</div>
                </div>
                <div className="impact-card" style={{ background: 'rgba(244, 63, 94, 0.05)', border: '1px solid rgba(244, 63, 94, 0.1)' }}>
                    <div style={{ color: '#f43f5e', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem' }}>CẮT LỖ</div>
                    <div style={{ fontSize: '1.8rem', fontWeight: 700 }}>{result.stop_loss?.toLocaleString()}</div>
                </div>
                <div className={`impact-card ${trendMeta.cardClass}`}>
                    <div className={`impact-header ${trendMeta.textClass}`}>
                        {trendMeta.icon} XU HƯỚNG
                    </div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 600, textTransform: 'uppercase' }}>{trendMeta.label}</div>
                </div>

                {/* Sentiment Card */}
                {result.sentiment_label && (
                    <div className="impact-card" style={{ background: `rgba(${sentimentColor === '#22c55e' ? '34,197,94' : sentimentColor === '#f43f5e' ? '244,63,94' : '148,163,184'}, 0.05)`, border: `1px solid ${sentimentColor}33` }}>
                        <div style={{ color: sentimentColor, fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <Newspaper size={14} /> TÂM LÝ THỊ TRƯỜNG
                        </div>
                        <div style={{ fontSize: '1.3rem', fontWeight: 700, color: sentimentColor }}>{result.sentiment_label}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                            {result.news_count > 0 ? `${result.news_count} bài báo` : 'Không có tin tức'}
                            {sentimentPct !== null && ` · ${sentimentPct}% tích cực`}
                        </div>
                    </div>
                )}
            </div>

            {/* Price History Chart */}
            {chartData.length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    style={{ marginBottom: '2rem', padding: '1.5rem', borderRadius: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}
                >
                    <h3 style={{ margin: '0 0 1.2rem 0', fontSize: '0.85rem', fontWeight: 800, letterSpacing: '1.5px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <TrendingUp size={16} /> BIỂU ĐỒ GIÁ (60 NGÀY GẦN NHẤT)
                    </h3>
                    <ResponsiveContainer width="100%" height={280}>
                        <LineChart data={chartData} margin={{ top: 15, right: 15, left: 0, bottom: 15 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                            <XAxis
                                dataKey="date"
                                tick={{ fill: '#64748b', fontSize: 11 }}
                                tickLine={false}
                                axisLine={false}
                                interval={9}
                                dy={8}
                            />
                            <YAxis
                                domain={['auto', 'auto']}
                                tick={{ fill: '#64748b', fontSize: 11 }}
                                tickLine={false}
                                axisLine={false}
                                width={50}
                                dx={-4}
                            />
                            <Tooltip
                                contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: '12px' }}
                                labelStyle={{ color: '#94a3b8', marginBottom: '4px' }}
                                itemStyle={{ color: '#f8fafc' }}
                            />
                            <Legend wrapperStyle={{ color: '#94a3b8', fontSize: '11px', paddingTop: '8px' }} />
                            <Line type="monotone" dataKey="close" stroke="#38bdf8" dot={false} strokeWidth={2} name="Giá đóng cửa" connectNulls />
                            <Line type="monotone" dataKey="ma5" stroke="#22c55e" dot={false} strokeWidth={1.5} strokeDasharray="4 2" name="MA5" connectNulls />
                            <Line type="monotone" dataKey="ma20" stroke="#f59e0b" dot={false} strokeWidth={1.5} strokeDasharray="4 2" name="MA20" connectNulls />
                        </LineChart>
                    </ResponsiveContainer>
                </motion.div>
            )}

            {/* Investment Strategy */}
            {result.investment_strategy && (
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '1.5rem', borderRadius: '12px', borderLeft: '4px solid var(--primary-color)', marginBottom: '2rem' }}>
                    <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: 'var(--primary-color)' }}>CHIẾN LƯỢC ĐẦU TƯ</h4>
                    <p style={{ margin: 0, fontSize: '1.1rem', lineHeight: '1.6' }}>{result.investment_strategy}</p>
                </div>
            )}

            <div className="report-body">
                {result.quote && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="quote-section"
                    >
                        <div className="quote-icon"><Clock size={24} /></div>
                        <div className="quote-content">
                            <p className="quote-text">"{result.quote.content}"</p>
                            <p className="quote-author">— {result.quote.author}</p>
                        </div>
                        <div className="quote-footer">
                            <span className="quote-badge">Bí kíp đầu tư</span>
                        </div>
                    </motion.div>
                )}


                <h3 className="section-title">
                    <BarChart3 size={24} /> BÁO CÁO CHI TIẾT
                </h3>
                <TechnicalDashboard result={result} />

                {result.agent_trace && (
                    <div className="agent-trace-section" style={{ marginTop: '3rem', padding: '2rem', background: 'rgba(0,0,0,0.15)', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                        <h4 style={{ marginTop: 0, marginBottom: '2rem', color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 800, letterSpacing: '2px', textTransform: 'uppercase' }}>
                            QUY TRÌNH PHÂN TÍCH CỦA TÁC NHÂN AI
                        </h4>
                        <div className="agent-stepper-container">
                            {result.agent_trace.map((step, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: i * 0.1 }}
                                    className={`agent-step ${step.status === 'completed' ? 'completed' : ''}`}
                                >
                                    <div className="step-left">
                                        <div className="step-icon-wrapper">
                                            {getAgentIcon(step.agent)}
                                        </div>
                                        <div className="step-line"></div>
                                    </div>
                                    <div className="step-content">
                                        <div className="step-title-row">
                                            <div className="step-title">{step.agent}</div>
                                            <div className="step-status-tag status-completed">
                                                <div className="pulse-dot"></div>
                                                {step.status}
                                            </div>
                                        </div>
                                        <div className="step-description">
                                            {step.data || step.tools?.join(', ') || step.logic || "Đã hoàn thành phân tích các chỉ số liên quan."}
                                        </div>
                                        {step.sentiment && (
                                            <div style={{ marginTop: '0.3rem', fontSize: '0.78rem', color: getSentimentColor(step.sentiment) }}>
                                                Tâm lý: {step.sentiment}
                                            </div>
                                        )}
                                        {step.overall_assessment && (
                                            <div style={{ marginTop: '0.3rem', fontSize: '0.78rem', color: getAssessmentStyle(step.overall_assessment).color }}>
                                                Đánh giá: {step.overall_assessment}
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export default AnalysisResult;
