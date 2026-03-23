import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, AlertCircle, BarChart3 } from 'lucide-react';

const Loader = ({ loading, error, result }) => {
    return (
        <AnimatePresence mode="wait">
            {loading && (
                <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="glass-card loading-area"
                >
                    <Activity className="animate-spin" size={64} color="var(--primary)" />
                    <h3 style={{ marginTop: '2rem' }}>Đang điều phối tác nhân AI...</h3>
                    <p style={{ color: 'var(--text-muted)' }}>
                        Các chuyên gia đang thu thập tin tức và phân tích chỉ số tài chính. 
                        Quá trình này có thể mất 1-2 phút.
                    </p>
                </motion.div>
            )}

            {error && (
                <motion.div
                    key="error"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="glass-card"
                    style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <AlertCircle size={32} />
                        <p>{error}</p>
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
    );
};

export default Loader;
