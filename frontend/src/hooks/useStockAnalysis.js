import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const useStockAnalysis = () => {
    const [loading, setLoading]       = useState(false);
    const [result, setResult]         = useState(null);
    const [error, setError]           = useState(null);
    const [agentSteps, setAgentSteps] = useState([]);
    const { logout } = useAuth();

    const performAnalysis = async (symbol) => {
        if (!symbol) return;

        setLoading(true);
        setError(null);
        setResult(null);
        setAgentSteps([]);

        const token   = sessionStorage.getItem('token');
        const headers = token ? { Authorization: `Bearer ${token}` } : {};

        try {
            const response = await axios.post(
                `${API_BASE_URL}/stock/analyze/${symbol}`, {}, { headers }
            );
            const jobId = response.data.job_id;
            if (!jobId) throw new Error('Invalid response from server: missing job_id');

            const MAX_ATTEMPTS  = 90;   // 90 × 2s = 3 phút
            const POLL_INTERVAL = 2000; // poll mỗi 2s để UI cập nhật nhanh
            let attempt    = 0;
            let intervalId = null;

            return new Promise((resolve) => {
                const poll = async () => {
                    attempt += 1;
                    if (attempt > MAX_ATTEMPTS) {
                        clearInterval(intervalId);
                        setError('Timeout: quá trình phân tích mất quá 3 phút.');
                        setLoading(false);
                        resolve(null);
                        return;
                    }

                    try {
                        const statusRes = await axios.get(
                            `${API_BASE_URL}/stock/analyze/status/${jobId}`, { headers }
                        );
                        const jobData = statusRes.data;

                        // Cập nhật agent steps mỗi lần poll (chỉ khi chưa completed)
                        if (jobData.agent_steps?.length && jobData.status !== 'completed') {
                            setAgentSteps(jobData.agent_steps);
                        }

                        if (jobData.status === 'completed') {
                            clearInterval(intervalId);

                            const s = jobData.agent_steps || [];
                            const mrDetail = s[0]?.detail || '';
                            const faDetail = s[1]?.detail || '';
                            const iaDetail = s[2]?.detail || '';

                            const step = (name, status, detail) => ({ name, status, detail });

                            // Bước 1: MR xong, FA bắt đầu chạy ngay
                            setAgentSteps([
                                step('Market Researcher',  'completed', mrDetail),
                                step('Financial Analyst',  'running',   'Tính RSI · MACD · ADX · Bollinger Bands'),
                                step('Investment Advisor', 'pending',   ''),
                            ]);

                            // Bước 2 (+1.4s): FA xong, IA bắt đầu chạy
                            setTimeout(() => setAgentSteps([
                                step('Market Researcher',  'completed', mrDetail),
                                step('Financial Analyst',  'completed', faDetail),
                                step('Investment Advisor', 'running',   'Chấm điểm tín hiệu & đưa ra khuyến nghị'),
                            ]), 1400);

                            // Bước 3 (+2.8s): IA xong
                            setTimeout(() => setAgentSteps([
                                step('Market Researcher',  'completed', mrDetail),
                                step('Financial Analyst',  'completed', faDetail),
                                step('Investment Advisor', 'completed', iaDetail),
                            ]), 2800);

                            // Bước 4 (+3.5s): hiện kết quả
                            setTimeout(() => {
                                setResult(jobData.result);
                                setLoading(false);
                                resolve(jobData.result);
                            }, 3500);
                        } else if (jobData.status === 'failed') {
                            clearInterval(intervalId);
                            setError(jobData.error || 'Server processing failed.');
                            setLoading(false);
                            resolve(null);
                        }
                    } catch (pollErr) {
                        const status = pollErr.response?.status;
                        if (status === 401) {
                            clearInterval(intervalId);
                            setLoading(false);
                            resolve(null);
                            logout(); // token hết hạn hoặc key mismatch → force logout
                        } else if (status !== 404) {
                            clearInterval(intervalId);
                            setError('Lỗi kết nối đến server.');
                            setLoading(false);
                            resolve(null);
                        }
                        // 404 → job chưa sẵn sàng → tiếp tục poll
                    }
                };

                intervalId = setInterval(poll, POLL_INTERVAL);
            });

        } catch (err) {
            setError(err.response?.data?.detail || 'Analysis failed.');
            setLoading(false);
            return null;
        }
    };

    return { loading, result, error, agentSteps, setResult, performAnalysis };
};
