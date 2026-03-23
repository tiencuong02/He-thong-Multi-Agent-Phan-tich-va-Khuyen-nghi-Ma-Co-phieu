import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useStockAnalysis } from '../hooks/useStockAnalysis';
import SearchBar from './SearchBar';
import Loader from './Loader';
import AnalysisResult from './AnalysisResult';
import HistorySidebar from './HistorySidebar';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const Dashboard = () => {
    const [ticker, setTicker] = useState('');
    const [history, setHistory] = useState([]);
    const { loading, result, error, setResult, performAnalysis } = useStockAnalysis();

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
        const newResult = await performAnalysis(ticker);
        if (newResult) {
            setHistory(prev => [newResult, ...prev.slice(0, 9)]);
        }
    };

    return (
        <div className="container">
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
