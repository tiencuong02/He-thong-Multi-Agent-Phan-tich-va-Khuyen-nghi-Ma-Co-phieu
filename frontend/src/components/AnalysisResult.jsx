import React from 'react';
import { motion } from 'framer-motion';
import { Clock, BarChart3, TrendingUp, TrendingDown, Globe, Search, Zap, CheckCircle2 } from 'lucide-react';

const getBadgeClass = (rec) => {
    const r = rec.toUpperCase();
    if (r.includes('BUY')) return 'badge badge-buy';
    if (r.includes('SELL')) return 'badge badge-sell';
    return 'badge badge-hold';
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

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card"
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2rem' }}>
                <div>
                    <h2 style={{ fontSize: '2.5rem', margin: 0 }}>{result.ticker}</h2>
                    <p style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Clock size={16} /> Cập nhật lúc {new Date(result.created_at).toLocaleTimeString()}
                    </p>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
                    <div className={getBadgeClass(result.recommendation)}>
                        {result.recommendation}
                    </div>
                    {result.fallback_used && (
                        <span style={{ fontSize: '0.7rem', background: 'rgba(234, 179, 8, 0.1)', color: '#eab308', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(234, 179, 8, 0.2)' }}>
                            ⚠️ Dữ liệu mô phỏng
                        </span>
                    )}
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
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
            </div>

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
                        <div className="quote-icon">
                            <Clock size={24} />
                        </div>
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
                <div className="report-text">
                    {result.risk_opportunity}
                </div>

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
