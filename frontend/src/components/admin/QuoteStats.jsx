import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';
import { Users, Quote as QuoteIcon, TrendingUp, Activity, Loader2, ArrowUpRight } from 'lucide-react';
import StatCard from './StatCard';

const QuoteStats = () => {
  const [stats, setStats] = useState([]);
  const [userStats, setUserStats] = useState([]);
  const [stockStats, setStockStats] = useState({ top_tickers: [], recommendations: [] });
  const [summary, setSummary] = useState({ totalQuotes: 0, totalViews: 0 });
  const [loading, setLoading] = useState(true);

  const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const [statsRes, userStatsRes, stockStatsRes] = await Promise.all([
        axios.get(`${API_URL}/quotes/stats/`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/quotes/stats/by-user/`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/stock/stats/`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setStats(statsRes.data.detailed || []);
      setUserStats(userStatsRes.data || []);
      setStockStats(stockStatsRes.data || { top_tickers: [], recommendations: [] });
      
      // Store summary for header cards
      setSummary({
        totalQuotes: statsRes.data.total_quotes || 0,
        totalViews: statsRes.data.total_views || 0
      });
    } catch (error) {
      console.error('Failed to fetch statistics', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="h-96 flex items-center justify-center">
      <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
    </div>
  );

  const totalShows = stats.reduce((sum, s) => sum + s.count, 0);
  const activeUsers = userStats.length;

  const COLORS = ['#38bdf8', '#818cf8', '#a78bfa', '#f472b6', '#fb7185'];

  return (
    <div className="fade-in">
      {/* Quick Stats */}
      <div className="stat-grid">
        <StatCard
          title="Quote Views"
          value={summary.totalViews}
          icon={Activity}
          trend="up"
          trendValue="14%"
          description="Engagement rate"
        />
        <StatCard
          title="Active Users"
          value={userStats.length}
          icon={Users}
          trend="up"
          trendValue="+3"
          description="Active today"
        />
        <StatCard
          title="Quotes DB"
          value={summary.totalQuotes}
          icon={QuoteIcon}
          description="Total database entries"
        />
        <StatCard
          title="System Core"
          value="Healthy"
          icon={ArrowUpRight}
          description="Service status normal"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Most Searched Stocks */}
        <div className="admin-section">
          <div className="section-header">
            <h3 className="section-title">
              <TrendingUp size={18} /> Top Content (Quotes)
            </h3>
          </div>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.slice(0, 5)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" horizontal={false} />
                <XAxis type="number" hide />
                <YAxis
                  dataKey="author"
                  type="category"
                  tick={{ fill: '#64748b', fontSize: 11, fontWeight: 600 }}
                  width={100}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid rgba(255,255,255,0.05)',
                    borderRadius: '12px'
                  }}
                  itemStyle={{ color: '#fff' }}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={24}>
                  {stats.slice(0, 5).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Searched Stocks */}
        <div className="admin-section">
          <div className="section-header">
            <h3 className="section-title">
              <Activity size={18} /> Top Searched Stocks
            </h3>
          </div>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stockStats.top_tickers} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" horizontal={false} />
                <XAxis type="number" hide />
                <YAxis
                  dataKey="ticker"
                  type="category"
                  tick={{ fill: '#64748b', fontSize: 11, fontWeight: 800 }}
                  width={60}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid rgba(255,255,255,0.05)',
                    borderRadius: '12px'
                  }}
                  itemStyle={{ color: '#fff' }}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={24} fill="#6366f1" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* User Activity */}
        <div className="admin-section">
          <div className="section-header">
            <h3 className="section-title">
              <Users size={18} /> Active Users (Quote interactions)
            </h3>
          </div>
          <div className="grid gap-3">
            {userStats.slice(0, 5).map((u, i) => (
              <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500/20 to-blue-500/20 flex items-center justify-center text-blue-400 font-bold border border-blue-500/10">
                    {(u.username || u.user_id || '?').charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="font-bold text-sm text-gray-200">{u.username || u.user_id?.slice(0, 8) + '...'}</p>
                    <p className="text-xs text-gray-500 truncate max-w-[200px]">Top content: {u.most_used_content}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-black text-blue-400">{u.total_shown}</p>
                  <p className="text-[10px] text-gray-600 uppercase tracking-widest font-bold">Views</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Global Recommendations */}
        <div className="admin-section">
          <div className="section-header">
            <h3 className="section-title">
              <ArrowUpRight size={18} /> Global Recommendations
            </h3>
          </div>
          <div className="grid gap-3">
            {stockStats.recommendations.map((r, i) => (
              <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="flex items-center gap-4">
                  <div className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-widest ${
                      r.recommendation.toUpperCase().includes('BUY') ? 'bg-green-500/20 text-green-400' :
                      r.recommendation.toUpperCase().includes('SELL') ? 'bg-red-500/20 text-red-400' :
                      'bg-blue-500/20 text-blue-400'
                  }`}>
                    {r.recommendation}
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-black text-gray-200">{r.count}</p>
                  <p className="text-[10px] text-gray-600 uppercase tracking-widest font-bold">Times</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuoteStats;
