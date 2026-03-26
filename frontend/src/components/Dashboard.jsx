import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useStockAnalysis } from '../hooks/useStockAnalysis';
import { User, LogOut, LayoutDashboard } from 'lucide-react';
import SearchBar from './SearchBar';
import Loader from './Loader';
import AnalysisResult from './AnalysisResult';
import HistorySidebar from './HistorySidebar';
import ProfileModal from './ProfileModal';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const Dashboard = () => {
    const [ticker, setTicker] = useState('');
    const [history, setHistory] = useState([]);
    const [featured, setFeatured] = useState(null);
    const [isProfileOpen, setIsProfileOpen] = useState(false);
    const { loading, result, error, setResult, performAnalysis } = useStockAnalysis();
    const { user, login } = useAuth(); // or fetchUser if I exported it
    const { logout, fetchUser } = useAuth(); // Need fetchUser from AuthContext

    useEffect(() => {
        fetchHistory();
        fetchFeatured();
    }, []);

    const fetchHistory = async () => {
        const token = localStorage.getItem('token');
        try {
            const response = await axios.get(`${API_BASE_URL}/stock/history`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setHistory(response.data);
        } catch (err) {
            console.error('Failed to fetch history', err);
        }
    };

    const fetchFeatured = async () => {
        const token = localStorage.getItem('token');
        try {
            const response = await axios.get(`${API_BASE_URL}/stock/featured`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setFeatured(response.data);
        } catch (err) {
            console.error('Failed to fetch featured stock', err);
        }
    };

    const getGreeting = () => {
        if (!user) return 'Chào bạn';
        const currentYear = new Date().getFullYear();
        // user.dob format is YYYY-MM-DD
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
            fetchHistory(); // Refresh history after new analysis
        }
    };

    return (
        <div className="container">
            <div className="user-bar">
                <div className="user-info">
                    <User size={16} />
                    <span>{user?.username} ({user?.role === 'ADMIN' ? 'Quản trị viên' : 'Nhà đầu tư'})</span>
                </div>
                <div className="user-actions">
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

            <div className="welcome-banner fade-in">
                <div className="welcome-content">
                    <h2>{getGreeting()} {user?.username},</h2>
                    <p>Hãy cùng robot AI tìm kiếm cơ hội đầu tư tốt nhất hôm nay.</p>
                </div>
                {featured && (
                    <div className="featured-rec" onClick={() => setTicker(featured.ticker)} style={{ cursor: 'pointer' }}>
                        <div className="featured-tag">GỢI Ý TỪ ROBOT {user?.investment_style === 'short_term' ? 'SHORT-TERM' : 'LONG-TERM'}</div>
                        <div className="featured-main">
                            <span className="featured-ticker">{featured.ticker}</span>
                            <span className="badge badge-buy">{featured.recommendation}</span>
                        </div>
                        <div className="featured-reason">{featured.reason}</div>
                    </div>
                )}
            </div>

            <header className="fade-in" style={{ textAlign: 'left', marginBottom: '2.5rem' }}>
                <h1 style={{ textAlign: 'left', fontSize: '2.5rem' }}>Multi-Agent Stock Advisor</h1>
            </header>

            <SearchBar
                ticker={ticker}
                setTicker={setTicker}
                handleAnalyze={handleAnalyze}
                loading={loading}
            />

            <div className="dashboard-grid">
                <div className="main-content">
                    <Loader loading={loading} error={error} result={result} />
                    <AnalysisResult result={result} />
                </div>

                <HistorySidebar
                    history={history}
                    onResultClick={(item) => setResult(item)}
                />
            </div>

            {isProfileOpen && (
                <ProfileModal
                    user={user}
                    onClose={() => setIsProfileOpen(false)}
                    onUpdate={() => {
                        const token = localStorage.getItem('token');
                        fetchUser(token);
                        fetchFeatured();
                    }}
                />
            )}
        </div>
    );
};

export default Dashboard;
