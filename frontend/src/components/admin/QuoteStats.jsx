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
        {/* User Activity */}
        <div className="admin-section">
          <div className="section-header">
            <h3 className="section-title">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(34, 197, 230, 0.2))', borderRadius: '8px' }}>
                <Users size={18} style={{ color: '#22d3ee' }} />
              </div>
              Active Users (Quote interactions)
            </h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px', marginTop: '1rem' }}>
            {userStats.slice(0, 5).map((u, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '16px',
                  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.5), rgba(30, 41, 59, 0.5))',
                  border: '1px solid rgba(71, 85, 105, 0.5)',
                  borderRadius: '12px',
                  transition: 'all 0.3s ease',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(34, 197, 230, 0.6)';
                  e.currentTarget.style.boxShadow = '0 8px 16px rgba(34, 197, 230, 0.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(71, 85, 105, 0.5)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                  <div style={{
                    width: '48px',
                    height: '48px',
                    minWidth: '48px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(34, 197, 230, 0.3))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '18px',
                    fontWeight: 'bold',
                    color: '#67e8f9',
                    border: '2px solid rgba(34, 197, 230, 0.3)',
                    transition: 'all 0.3s ease'
                  }}>
                    {(u.username || u.user_id || '?').charAt(0).toUpperCase()}
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <p style={{ margin: '0 0 4px 0', fontSize: '14px', fontWeight: '600', color: '#f1f5f9', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {u.username || u.user_id?.slice(0, 8) + '...'}
                    </p>
                    <p style={{ margin: '0', fontSize: '12px', color: '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '250px' }}>
                      {u.most_used_content}
                    </p>
                  </div>
                </div>
                <div style={{ textAlign: 'right', marginLeft: '16px', minWidth: 'fit-content' }}>
                  <p style={{ margin: '0', fontSize: '24px', fontWeight: '800', background: 'linear-gradient(90deg, #38bdf8, #22d3ee)', backgroundClip: 'text', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', color: 'transparent' }}>
                    {u.total_shown}
                  </p>
                  <p style={{ margin: '4px 0 0 0', fontSize: '10px', color: '#64748b', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Views
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Global Recommendations */}
        <div className="admin-section">
          <div className="section-header">
            <h3 className="section-title">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', background: 'linear-gradient(135deg, rgba(217, 119, 6, 0.2), rgba(249, 115, 22, 0.2))', borderRadius: '8px' }}>
                <ArrowUpRight size={18} style={{ color: '#fbbf24' }} />
              </div>
              Global Recommendations
            </h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px', marginTop: '1rem' }}>
            {stockStats.recommendations.map((r, i) => {
              const isRecommendation = r.recommendation?.toUpperCase() || '';
              const isBuy = isRecommendation.includes('BUY');
              const isSell = isRecommendation.includes('SELL');
              const isHold = isRecommendation.includes('HOLD');

              let bgGradient, borderColor, shadowColor, badgeBg, badgeColor, textColor;
              if (isBuy) {
                bgGradient = 'linear-gradient(135deg, rgba(5, 46, 22, 0.4), rgba(6, 78, 59, 0.4))';
                borderColor = 'rgba(34, 197, 94, 0.5)';
                shadowColor = 'rgba(34, 197, 94, 0.1)';
                badgeBg = 'rgba(34, 197, 94, 0.2)';
                badgeColor = '#4ade80';
                textColor = '#4ade80';
              } else if (isSell) {
                bgGradient = 'linear-gradient(135deg, rgba(127, 29, 29, 0.4), rgba(153, 27, 27, 0.4))';
                borderColor = 'rgba(239, 68, 68, 0.5)';
                shadowColor = 'rgba(239, 68, 68, 0.1)';
                badgeBg = 'rgba(239, 68, 68, 0.2)';
                badgeColor = '#ef4444';
                textColor = '#ef4444';
              } else {
                bgGradient = 'linear-gradient(135deg, rgba(15, 23, 42, 0.4), rgba(30, 41, 59, 0.4))';
                borderColor = 'rgba(71, 85, 105, 0.5)';
                shadowColor = 'rgba(34, 197, 230, 0.1)';
                badgeBg = 'rgba(34, 197, 230, 0.2)';
                badgeColor = '#22d3ee';
                textColor = '#22d3ee';
              }

              return (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '16px',
                    background: bgGradient,
                    border: `1px solid ${borderColor}`,
                    borderRadius: '12px',
                    transition: 'all 0.3s ease',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = textColor;
                    e.currentTarget.style.boxShadow = `0 8px 16px ${shadowColor}`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = borderColor;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <div style={{
                    padding: '8px 16px',
                    background: badgeBg,
                    borderRadius: '8px',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    color: badgeColor,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    transition: 'all 0.3s ease'
                  }}>
                    {r.recommendation}
                  </div>
                  <div style={{ textAlign: 'right', minWidth: 'fit-content' }}>
                    <p style={{ margin: '0', fontSize: '24px', fontWeight: '800', color: textColor }}>
                      {r.count}
                    </p>
                    <p style={{ margin: '4px 0 0 0', fontSize: '10px', color: '#64748b', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Times
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuoteStats;
