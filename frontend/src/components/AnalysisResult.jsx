import React from 'react';
import { motion } from 'framer-motion';
import { Clock, BarChart3, TrendingUp, TrendingDown } from 'lucide-react';

const getBadgeClass = (rec) => {
    const r = rec.toUpperCase();
    if (r.includes('BUY'))  return 'badge badge-buy';
    if (r.includes('SELL')) return 'badge badge-sell';
    return 'badge badge-hold';
};

const AnalysisResult = ({ result }) => {
    if (!result) return null;

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
                <div className={getBadgeClass(result.recommendation)}>
                    {result.recommendation}
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                <div className="impact-card impact-opportunity">
                    <div className="impact-header opportunity-text">
                        <TrendingUp size={20} /> CƠ HỘI
                    </div>
                    <p>{result.risk_opportunity.split('\n')[0]}</p>
                </div>
                <div className="impact-card impact-risk">
                    <div className="impact-header risk-text">
                        <TrendingDown size={20} /> RỦI RO
                    </div>
                    <p>{result.risk_opportunity.split('\n')[1] || "Đang đánh giá rủi ro hệ thống và thanh khoản."}</p>
                </div>
            </div>

            <div className="report-body">
                <h3 className="section-title">
                    <BarChart3 size={24} /> BÁO CÁO CHI TIẾT
                </h3>
                <div className="report-text">
                    {result.risk_opportunity}
                </div>
                
                {result.agent_trace && (
                    <div className="agent-trace">
                        <h4>Luồng suy luận của Tác nhân</h4>
                        <ul>
                            {result.agent_trace.map((step, i) => (
                                <li key={i}>
                                    <strong>{step.agent}</strong>: {step.status} 
                                    {step.tools && <span className="trace-tools">[{step.tools.join(', ')}]</span>}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export default AnalysisResult;
