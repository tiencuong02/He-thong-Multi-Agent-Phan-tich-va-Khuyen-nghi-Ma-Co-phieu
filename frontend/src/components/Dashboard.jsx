import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useStockAnalysis } from '../hooks/useStockAnalysis';
import { User, LogOut, LayoutDashboard } from 'lucide-react';
import SearchBar from './SearchBar';
import Loader from './Loader';
import AnalysisResult from './AnalysisResult';
import HistorySidebar from './HistorySidebar';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const Dashboard = () => {
    const [ticker, setTicker] = useState('');
    const [history, setHistory] = useState([]);
    const { loading, result, error, setResult, performAnalysis } = useStockAnalysis();
    const { user, logout } = useAuth();

    useEffect(() => {
        fetchHistory();
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
                    <span>{user?.username} ({user?.role})</span>
                </div>
                <div className="user-actions">
                    {user?.role === 'ADMIN' && (
                        <a href="/admin" className="admin-link">
                            <LayoutDashboard size={16} /> Admin Panel
                        </a>
                    )}
                    <button onClick={logout} className="logout-btn">
                        <LogOut size={16} /> Logout
                    </button>
                </div>
            </div>

            <header className="fade-in">
                <h1>Multi-Agent Stock Advisor</h1>
                <p className="subtitle">Hệ thống phân tích Đa tác nhân thông minh cho thị trường chứng khoán</p>
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
        </div>
    );
};

export default Dashboard;
