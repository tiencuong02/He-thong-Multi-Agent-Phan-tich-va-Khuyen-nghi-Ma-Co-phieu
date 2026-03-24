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
  const [loading, setLoading] = useState(true);

  const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const [statsRes, userStatsRes] = await Promise.all([
        axios.get(`${API_URL}/quotes/stats`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/quotes/stats/by-user`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setStats(statsRes.data);
      setUserStats(userStatsRes.data);
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
          value={totalShows} 
          icon={Activity} 
          trend="up" 
          trendValue="14%" 
          description="Engagement rate"
        />
        <StatCard 
          title="Active Users" 
          value={activeUsers} 
          icon={Users} 
          trend="up" 
          trendValue="+3" 
          description="Active today"
        />
        <StatCard 
          title="Quotes DB" 
          value={stats.length} 
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
        {/* Most Shown Quotes */}
        <div className="admin-section">
          <div className="section-header">
            <h3 className="section-title">
              <TrendingUp size={18} /> Engagement metrics
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
                    borderRadius: '12px',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.4)'
                  }}
                  itemStyle={{ color: '#fff' }}
                  cursor={{ fill: '#ffffff05' }}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={32}>
                  {stats.slice(0, 5).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* User Activity */}
        <div className="admin-section">
          <div className="section-header">
            <h3 className="section-title">
              <Users size={18} /> Top contributors
            </h3>
          </div>
          <div className="grid gap-3">
            {userStats.slice(0, 5).map((u, i) => (
              <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-blue-500/20 transition-all group">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500/20 to-blue-500/20 flex items-center justify-center text-blue-400 font-bold border border-blue-500/10 transition-transform group-hover:scale-110">
                    {u.user_id.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="font-bold text-sm text-gray-200">{u.user_id}</p>
                    <p className="text-xs text-gray-500 truncate max-w-[200px]">Top content: {u.most_used_content}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-black text-blue-400">{u.total_shown}</p>
                  <p className="text-[10px] text-gray-600 uppercase tracking-widest font-bold">Views</p>
                </div>
              </div>
            ))}
            {userStats.length === 0 && (
                <div className="py-12 text-center text-gray-600">
                    <Activity size={32} className="mx-auto mb-2 opacity-20" />
                    <p className="text-sm">No activity records yet</p>
                </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuoteStats;
