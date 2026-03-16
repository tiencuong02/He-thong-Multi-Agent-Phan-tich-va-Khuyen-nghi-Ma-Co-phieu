import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Activity, AlertCircle, Clock, BarChart3, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE_URL = 'http://localhost:8000';

const Dashboard = () => {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/history`);
      setHistory(response.data);
    } catch (err) {
      console.error('Failed to fetch history', err);
    }
  };

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!ticker) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/analyze/${ticker}`);
      setResult(response.data);
      fetchHistory();
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const getBadgeClass = (rec) => {
    if (rec.includes('Buy')) return 'badge badge-buy';
    if (rec.includes('Sell')) return 'badge badge-sell';
    return 'badge badge-hold';
  };

  return (
    <div className="container">
      <header className="fade-in">
        <h1>Multi-Agent Stock Advisor</h1>
        <p className="subtitle">Hệ thống phân tích Đa tác nhân thông minh cho thị trường chứng khoán</p>
      </header>

      <form onSubmit={handleAnalyze} className="search-group fade-in">
        <div className="input-wrapper">
          <Search className="search-icon" size={24} />
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="Nhập mã cổ phiếu (ví dụ: VNM, FPT...)"
          />
        </div>
        <button disabled={loading} type="submit" className="btn-primary">
          {loading ? <RefreshCw className="animate-spin" /> : 'Phân tích'}
        </button>
      </form>

      <div className="dashboard-grid">
        <div className="main-content">
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
                <h3 style={{ marginTop: '2rem' }}>Đang điều phối tác nhân...</h3>
                <p style={{ color: 'var(--text-muted)' }}>Các chuyên gia đang thu thập tin tức và phân tích chỉ số tài chính.</p>
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

            {result && (
              <motion.div
                key="result"
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
                  <div style={{ background: 'rgba(52, 211, 153, 0.05)', padding: '1.5rem', borderRadius: '1.5rem', border: '1px solid rgba(52, 211, 153, 0.1)' }}>
                    <div style={{ color: 'var(--secondary)', fontWeight: 800, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <TrendingUp size={20} /> CƠ HỘI
                    </div>
                    <p style={{ fontSize: '0.9rem' }}>{result.risk_opportunity.split('\n')[0]}</p>
                  </div>
                  <div style={{ background: 'rgba(248, 113, 113, 0.05)', padding: '1.5rem', borderRadius: '1.5rem', border: '1px solid rgba(248, 113, 113, 0.1)' }}>
                    <div style={{ color: 'var(--danger)', fontWeight: 800, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <TrendingDown size={20} /> RỦI RO
                    </div>
                    <p style={{ fontSize: '0.9rem' }}>{result.risk_opportunity.split('\n')[1] || "Đang đánh giá rủi ro hệ thống và thanh khoản."}</p>
                  </div>
                </div>

                <div className="report-body">
                  <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary)' }}>
                    <BarChart3 size={24} /> BÁO CÁO CHI TIẾT
                  </h3>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '2rem', borderRadius: '1.5rem', whiteSpace: 'pre-line' }}>
                    {result.risk_opportunity}
                  </div>
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
        </div>

        <aside className="fade-in" style={{ animationDelay: '0.2s' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
            <Clock size={24} color="var(--text-muted)" /> LỊCH SỬ GẦN ĐÂY
          </h3>
          <div className="history-list">
            {history.map((item, idx) => (
              <motion.div
                whileHover={{ scale: 1.02 }}
                key={idx}
                className="history-item"
                onClick={() => setResult(item)}
              >
                <div>
                  <div style={{ fontWeight: 800, fontSize: '1.1rem' }}>{item.ticker}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {new Date(item.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div style={{ fontWeight: 700, color: item.recommendation.includes('Buy') ? 'var(--secondary)' : item.recommendation.includes('Sell') ? 'var(--danger)' : 'var(--warning)' }}>
                  {item.recommendation}
                </div>
              </motion.div>
            ))}
            {history.length === 0 && (
              <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontStyle: 'italic' }}>Chưa có dữ liệu.</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};

export default Dashboard;
