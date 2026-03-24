import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Quote, MessageSquare, Users, Activity, Clock } from 'lucide-react';
import StatCard from './StatCard';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const DashboardOverview = () => {
    const [stats, setStats] = useState({
        total: 0,
        byContext: {},
        recentLogs: []
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            const token = localStorage.getItem('token');
            const [statsRes, logsRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/quotes/stats`, {
                    headers: { Authorization: `Bearer ${token}` }
                }),
                axios.get(`${API_BASE_URL}/quotes/stats/by-user`, {
                    headers: { Authorization: `Bearer ${token}` }
                })
            ]);
            
            // Note: Adjusting based on actual API response structure
            setStats({
                total: statsRes.data.total_quotes || 0,
                byContext: statsRes.data.by_context || {},
                recentLogs: logsRes.data || []
            });
        } catch (err) {
            console.error('Failed to fetch stats', err);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div className="loading-area">Loading stats...</div>;
    }

    return (
        <div className="fade-in">
            <div className="stat-grid">
                <StatCard 
                    title="Total Quotes" 
                    value={stats.total} 
                    icon={Quote} 
                    trend="up" 
                    trendValue="+8%" 
                    description="vs last month"
                />
                <StatCard 
                    title="Buy Context" 
                    value={stats.byContext.BUY || 0} 
                    icon={Activity} 
                    description="Active recommendations"
                />
                <StatCard 
                    title="Sell Context" 
                    value={stats.byContext.SELL || 0} 
                    icon={MessageSquare} 
                    description="Market warnings"
                />
                <StatCard 
                    title="Active Users" 
                    value={Object.keys(stats.recentLogs).length} 
                    icon={Users} 
                    trendValue="12" 
                    description="Users tracked"
                />
            </div>

            <div className="admin-section">
                <div className="section-header">
                    <h3 className="section-title">
                        <Clock size={18} /> Recent Activity
                    </h3>
                </div>
                
                {stats.recentLogs.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead>
                                <tr className="text-gray-500 text-xs uppercase tracking-wider border-b border-white/5">
                                    <th className="pb-3 px-4">User</th>
                                    <th className="pb-3 px-4">Action</th>
                                    <th className="pb-3 px-4">Timestamp</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {stats.recentLogs.map((log, idx) => (
                                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                                        <td className="py-4 px-4 font-medium">{log.username || 'Anonymous'}</td>
                                        <td className="py-4 px-4 text-gray-400">Viewed Quote</td>
                                        <td className="py-4 px-4 text-gray-500 text-sm">
                                            {new Date().toLocaleTimeString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="py-12 text-center text-gray-500 bg-white/[0.01] rounded-xl border border-dashed border-white/5">
                        <Activity size={48} className="mx-auto mb-4 opacity-20" />
                        <p>No recent activity logs found</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default DashboardOverview;
