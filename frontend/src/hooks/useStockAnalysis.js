import { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const useStockAnalysis = () => {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const performAnalysis = async (symbol) => {
        if (!symbol) return;

        setLoading(true);
        setError(null);
        setResult(null);

        const token = localStorage.getItem('token');
        const headers = token ? { Authorization: `Bearer ${token}` } : {};

        try {
            const response = await axios.post(`${API_BASE_URL}/stock/analyze/${symbol}/`, {}, { headers });
            const jobId = response.data.job_id;

            if (!jobId) {
                throw new Error('Invalid response from server: missing job_id');
            }

            const MAX_ATTEMPTS = 60;
            const POLL_INTERVAL = 3000;
            let attempt = 0;
            let intervalId = null;

            return new Promise((resolve) => {
                const poll = async () => {
                    attempt += 1;
                    if (attempt > MAX_ATTEMPTS) {
                        clearInterval(intervalId);
                        setError('Timeout reached (3 minutes).');
                        setLoading(false);
                        resolve(null);
                        return;
                    }

                    try {
                        const statusRes = await axios.get(`${API_BASE_URL}/stock/analyze/status/${jobId}/`, { headers });
                        const jobData = statusRes.data;

                        if (jobData.status === 'completed') {
                            clearInterval(intervalId);
                            setResult(jobData.result);
                            setLoading(false);
                            resolve(jobData.result);
                        } else if (jobData.status === 'failed') {
                            clearInterval(intervalId);
                            setError(jobData.error || 'Server processing failed.');
                            setLoading(false);
                            resolve(null);
                        }
                    } catch (pollErr) {
                        if (pollErr.response?.status !== 404) {
                            clearInterval(intervalId);
                            setError('Connection error.');
                            setLoading(false);
                            resolve(null);
                        }
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

    return { loading, result, error, setResult, performAnalysis };
};
