
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useStockAnalysis } from '../hooks/useStockAnalysis';
import { User, LogOut, LayoutDashboard, Shield, Cpu, BarChart3, TrendingUp } from 'lucide-react';
import SearchBar from './SearchBar';
import Loader from './Loader';
import AnalysisResult from './AnalysisResult';
import HistorySidebar from './HistorySidebar';
import ProfileModal from './ProfileModal';
import ChatBotWidget from './ChatBotWidget';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const Dashboard = () => {
    const [ticker, setTicker] = useState('');
    const [history, setHistory] = useState([]);
    const [isProfileOpen, setIsProfileOpen] = useState(false);
    const { loading, result, error, agentSteps, setResult, performAnalysis } = useStockAnalysis();
    const { user, login } = useAuth();
    const { logout, fetchUser } = useAuth();

    useEffect(() => {
        fetchHistory();
    }, []);

    const fetchHistory = async () => {
        const token = sessionStorage.getItem('token');
        try {
            const response = await axios.get(`${API_BASE_URL}/stock/history/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setHistory(response.data);
        } catch (err) {
            console.error('Failed to fetch history', err);
        }
    };

    const getGreeting = () => {
        if (!user) return 'Chào bạn';
        const currentYear = new Date().getFullYear();
        const birthYear = user.dob ? parseInt(user.dob.split('-')[0]) : 1990;
        const age = currentYear - birthYear;
        const gender = user.gender || 'male';

        if (age > 55) return 'Chào Bác';
        if (gender === 'male') return 'Chào Anh';
        if (gender === 'female') return 'Chào Chị';
        return 'Chào bạn';
    };

    const handleAnalyze = async (e) => {
        e.preventDefault();
        const newResult = await performAnalysis(ticker);
        if (newResult) {
            fetchHistory();
        }
    };

    return (
        <div className="container">
            <div className="user-bar">
                <div className="navbar-logo">
                    <div className="navbar-logo-icon">
                        <TrendingUp size={20} />
                    </div>
                    <div className="navbar-logo-text">
                        <span className="navbar-brand-name">MASA</span>
                        <span className="navbar-brand-tagline">Stock Advisor</span>
                    </div>
                </div>
                <div className="user-actions">
                    <div className="user-info">
                        <User size={14} />
                        <span>{user?.username} ({user?.role === 'ADMIN' ? 'Quản trị viên' : 'Nhà đầu tư'})</span>
                    </div>
                    <button className="profile-btn" onClick={() => setIsProfileOpen(true)}>
                        Hồ sơ của tôi
                    </button>
                    {user?.role === 'ADMIN' && (
                        <a href="/admin" className="admin-link">
                            <LayoutDashboard size={16} /> Admin Panel
                        </a>
                    )}
                    <button onClick={logout} className="logout-btn">
                        <LogOut size={16} /> Đăng xuất
                    </button>
                </div>
            </div>

            <header className="fade-in" style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                <h1 style={{ textAlign: 'center', fontSize: 'clamp(2rem, 7vw, 4rem)', marginBottom: '0.25rem' }}>Multi-Agent Stock Advisor</h1>
                <p className="subtitle" style={{ marginBottom: '1rem', fontSize: '1.05rem' }}>
                    Hệ thống phân tích cổ phiếu bằng AI đa tác nhân — Chính xác, Nhanh chóng, Đáng tin cậy
                </p>
                <div style={{
                    display: 'flex',
                    justifyContent: 'center',
                    gap: '2rem',
                    flexWrap: 'wrap'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        <Cpu size={16} style={{ color: 'var(--primary)' }} />
                        <span>AI Multi-Agent</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        <BarChart3 size={16} style={{ color: 'var(--secondary)' }} />
                        <span>Phân tích kỹ thuật & cơ bản</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        <Shield size={16} style={{ color: 'var(--accent)' }} />
                        <span>Khuyến nghị uy tín</span>
                    </div>
                </div>
            </header>

            <SearchBar
                ticker={ticker}
                setTicker={setTicker}
                handleAnalyze={handleAnalyze}
                loading={loading}
            />

            <div className="dashboard-grid">
                <div className="main-content">
                    <Loader loading={loading} error={error} result={result} agentSteps={agentSteps} />
                    <AnalysisResult result={result} />
                </div>

                <HistorySidebar
                    history={history}
                    result={result}
                    onResultClick={(item) => setResult(item)}
                />
            </div>

            {isProfileOpen && (
                <ProfileModal
                    user={user}
                    onClose={() => setIsProfileOpen(false)}
                    onUpdate={() => {
                        const token = sessionStorage.getItem('token');
                        fetchUser(token);
                    }}
                />
            )}

            {/* Floating Chatbot Widget */}
            <ChatBotWidget user={user} />
        </div>
    );
};

export default Dashboard;
