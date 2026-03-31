import React from 'react';
import { motion } from 'framer-motion';
import { Clock, TrendingUp, TrendingDown, Minus } from 'lucide-react';

const HistorySidebar = ({ history, onResultClick }) => {
    return (
        <aside className="fade-in" style={{ animationDelay: '0.2s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                    <Clock size={24} color="var(--text-muted)" /> LỊCH SỬ GẦN ĐÂY
                </h3>
            </div>
            <div className="history-list">
                {history.map((item, idx) => (
                    <motion.div
                        whileHover={{ scale: 1.02 }}
                        key={idx}
                        className="history-item"
                        onClick={() => onResultClick(item)}
                    >
                        <div>
                            <div style={{ fontWeight: 800, fontSize: '1.1rem' }}>{item.ticker}</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {new Date(item.created_at).toLocaleDateString()}
                            </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            {item.trend === 'up' && <TrendingUp size={16} color="var(--secondary)" />}
                            {item.trend === 'down' && <TrendingDown size={16} color="var(--danger)" />}
                            {item.trend === 'stable' && <Minus size={16} color="var(--warning)" />}
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
                    <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontStyle: 'italic' }}>Chưa có dữ liệu.</p>
                )}
            </div>
        </aside>
    );
};

export default HistorySidebar;
