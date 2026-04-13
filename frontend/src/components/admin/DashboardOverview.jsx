import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Quote, MessageSquare, Users, Activity, Clock, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import StatCard from './StatCard';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const PAGE_SIZE = 10;

// ─── Helpers ────────────────────────────────────────────────────────────────
function timeAgo(isoString) {
    if (!isoString) return '—';
    const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

// ─── Expanded per-user logs ──────────────────────────────────────────────────
function UserLogs({ userId, token }) {
    const [logs, setLogs] = useState([]);
    const [skip, setSkip] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [loading, setLoading] = useState(false);

    const fetchLogs = useCallback(async (currentSkip = 0, reset = false) => {
        setLoading(true);
        try {
            const res = await axios.get(
                `${API_BASE_URL}/quotes/recent-logs/?user_id=${userId}&limit=${PAGE_SIZE}&skip=${currentSkip}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            const data = res.data || [];
            setLogs(prev => reset ? data : [...prev, ...data]);
            setHasMore(data.length === PAGE_SIZE);
        } catch (e) {
            console.error('Failed to load user logs', e);
        } finally {
            setLoading(false);
        }
    }, [userId, token]);

    useEffect(() => { fetchLogs(0, true); }, [fetchLogs]);

    const loadMore = () => {
        const next = skip + PAGE_SIZE;
        setSkip(next);
        fetchLogs(next);
    };

    return (
        <div className="bg-white/[0.02] rounded-lg mx-4 mb-3 p-3 border border-white/[0.04]">
            {logs.length === 0 && !loading && (
                <p className="text-xs text-gray-500 text-center py-2">No logs found</p>
            )}
            <div className="flex flex-col gap-1.5">
                {logs.map((log, i) => (
                    <div key={i} className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-white/[0.02] hover:bg-white/[0.04]">
                        <span className="text-xs text-indigo-400 font-mono">
                            {log.timestamp ? new Date(log.timestamp).toLocaleTimeString('vi-VN') : '—'}
                        </span>
                        <span className="text-xs text-gray-500">
                            {log.context || 'HOLD'} context
                        </span>
                        <span className="text-xs text-gray-600">{timeAgo(log.timestamp)}</span>
                    </div>
                ))}
            </div>
            {loading && <p className="text-xs text-gray-600 text-center pt-2">Loading…</p>}
            {hasMore && !loading && (
                <button
                    onClick={loadMore}
                    className="mt-2 w-full text-xs text-gray-500 hover:text-cyan-400 transition-colors py-1"
                >
                    Load more ↓
                </button>
            )}
        </div>
    );
}

// ─── Main component ──────────────────────────────────────────────────────────
const DashboardOverview = () => {
    const [stats, setStats] = useState({ total: 0, byContext: {} });
    const [summary, setSummary] = useState([]);   // grouped by user
    const [filterUser, setFilterUser] = useState('all');
    const [expandedUser, setExpandedUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const token = localStorage.getItem('token');

    useEffect(() => { fetchAll(); }, []);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const [statsRes, summaryRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/quotes/stats/`, { headers: { Authorization: `Bearer ${token}` } }),
                axios.get(`${API_BASE_URL}/quotes/activity-summary/`, { headers: { Authorization: `Bearer ${token}` } }),
            ]);
            setStats({
                total: statsRes.data.total_quotes || 0,
                byContext: statsRes.data.by_context || {},
            });
            setSummary(summaryRes.data || []);
        } catch (err) {
            console.error('Failed to fetch overview', err);
        } finally {
            setLoading(false);
        }
    };

    const filteredSummary = filterUser === 'all'
        ? summary
        : summary.filter(u => u.user_id === filterUser);

    if (loading) return <div className="loading-area">Loading stats...</div>;

    return (
        <div className="fade-in">
            {/* ── Stat Cards ── */}
            <div className="stat-grid">
                <StatCard title="Total Quotes" value={stats.total} icon={Quote} trend="up" trendValue="+8%" description="vs last month" />
                <StatCard title="Buy Context"  value={stats.byContext.BUY  || 0} icon={Activity}     description="Active recommendations" />
                <StatCard title="Hold Context" value={stats.byContext.HOLD || 0} icon={Clock}         description="Hold positions" />
                <StatCard title="Sell Context" value={stats.byContext.SELL || 0} icon={MessageSquare} description="Market warnings" />
                <StatCard title="Active Users" value={summary.length} icon={Users} trendValue={`${summary.length}`} description="Users tracked" />
            </div>

            {/* ── Recent Activity ── */}
            <div className="admin-section">
                <div className="section-header">
                    <h3 className="section-title"><Clock size={18} /> Recent Activity</h3>
                    <button onClick={fetchAll} className="text-gray-500 hover:text-cyan-400 transition-colors">
                        <RefreshCw size={15} />
                    </button>
                </div>

                {/* Filter bar */}
                <div className="flex gap-2 mb-4 flex-wrap">
                    <select
                        value={filterUser}
                        onChange={e => setFilterUser(e.target.value)}
                        className="text-xs bg-white/[0.04] border border-white/10 text-gray-300 rounded-lg px-3 py-1.5 outline-none focus:border-cyan-500/50 cursor-pointer"
                    >
                        <option value="all">All Users</option>
                        {summary.map(u => (
                            <option key={u.user_id} value={u.user_id}>{u.username}</option>
                        ))}
                    </select>
                    <span className="text-xs text-gray-600 self-center">
                        {filteredSummary.length} user{filteredSummary.length !== 1 ? 's' : ''}
                    </span>
                </div>

                {filteredSummary.length === 0 ? (
                    <div className="py-12 text-center text-gray-500 bg-white/[0.01] rounded-xl border border-dashed border-white/5">
                        <Activity size={48} className="mx-auto mb-4 opacity-20" />
                        <p>No activity found</p>
                    </div>
                ) : (
                    <div style={{
                        borderRadius: '12px',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        overflow: 'hidden',
                        background: 'rgba(255, 255, 255, 0.02)'
                    }}>
                        <table style={{ width: '100%', fontSize: '14px', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{
                                    background: 'linear-gradient(to right, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02))',
                                    borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
                                }}>
                                    <th style={{
                                        textAlign: 'left',
                                        fontSize: '11px',
                                        fontWeight: 'bold',
                                        color: '#22d3ee',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.1em',
                                        padding: '16px 24px',
                                        width: '48px'
                                    }}>#</th>
                                    <th style={{
                                        textAlign: 'left',
                                        fontSize: '11px',
                                        fontWeight: 'bold',
                                        color: '#22d3ee',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.1em',
                                        padding: '16px 24px',
                                        minWidth: '128px'
                                    }}>User</th>
                                    <th style={{
                                        textAlign: 'left',
                                        fontSize: '11px',
                                        fontWeight: 'bold',
                                        color: '#22d3ee',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.1em',
                                        padding: '16px 24px',
                                        minWidth: '160px'
                                    }}>Action</th>
                                    <th style={{
                                        textAlign: 'center',
                                        fontSize: '11px',
                                        fontWeight: 'bold',
                                        color: '#22d3ee',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.1em',
                                        padding: '16px 24px',
                                        width: '80px'
                                    }}>Count</th>
                                    <th style={{
                                        textAlign: 'right',
                                        fontSize: '11px',
                                        fontWeight: 'bold',
                                        color: '#22d3ee',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.1em',
                                        padding: '16px 24px',
                                        minWidth: '112px'
                                    }}>Last Seen</th>
                                    <th style={{ width: '32px', padding: '16px 24px' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredSummary.map((row, idx) => {
                                    const isOpen = expandedUser === row.user_id;
                                    return (
                                        <React.Fragment key={row.user_id}>
                                            <tr
                                                onClick={() => setExpandedUser(isOpen ? null : row.user_id)}
                                                style={{
                                                    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                                                    cursor: 'pointer',
                                                    transition: 'background-color 0.3s ease'
                                                }}
                                                onMouseEnter={(e) => {
                                                    e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)';
                                                }}
                                                onMouseLeave={(e) => {
                                                    e.currentTarget.style.backgroundColor = 'transparent';
                                                }}
                                            >
                                                <td style={{
                                                    padding: '16px 24px',
                                                    fontSize: '11px',
                                                    fontWeight: 'bold',
                                                    color: '#9ca3af',
                                                    transition: 'color 0.3s ease'
                                                }}
                                                onMouseEnter={(e) => { e.currentTarget.style.color = '#22d3ee'; }}
                                                onMouseLeave={(e) => { e.currentTarget.style.color = '#9ca3af'; }}
                                                >{idx + 1}</td>
                                                <td style={{
                                                    padding: '16px 24px',
                                                    fontWeight: '600',
                                                    color: '#f1f5f9'
                                                }}>
                                                    <div style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '12px',
                                                        transition: 'color 0.3s ease'
                                                    }}>
                                                        <div style={{
                                                            width: '32px',
                                                            height: '32px',
                                                            borderRadius: '50%',
                                                            background: 'linear-gradient(135deg, #22d3ee, #0ea5e9)',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                            fontSize: '12px',
                                                            fontWeight: 'bold',
                                                            color: '#fff',
                                                            flexShrink: 0
                                                        }}>
                                                            {row.username.charAt(0).toUpperCase()}
                                                        </div>
                                                        {row.username}
                                                    </div>
                                                </td>
                                                <td style={{ padding: '16px 24px' }}>
                                                    <span style={{
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        padding: '6px 12px',
                                                        borderRadius: '8px',
                                                        fontSize: '11px',
                                                        fontWeight: '600',
                                                        background: 'rgba(99, 102, 241, 0.15)',
                                                        color: '#a5b4fc',
                                                        border: '1px solid rgba(99, 102, 241, 0.3)',
                                                        whiteSpace: 'nowrap',
                                                        transition: 'background-color 0.3s ease'
                                                    }}
                                                    onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(99, 102, 241, 0.2)'; }}
                                                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'rgba(99, 102, 241, 0.15)'; }}
                                                    >
                                                        Viewed Quote
                                                    </span>
                                                </td>
                                                <td style={{
                                                    padding: '16px 24px',
                                                    textAlign: 'center'
                                                }}>
                                                    <span style={{
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        minWidth: '48px',
                                                        padding: '6px 12px',
                                                        borderRadius: '8px',
                                                        background: 'linear-gradient(to right, rgba(34, 211, 238, 0.2), rgba(59, 130, 246, 0.2))',
                                                        fontSize: '14px',
                                                        fontWeight: 'bold',
                                                        color: '#a5f3fc',
                                                        border: '1px solid rgba(34, 211, 238, 0.3)'
                                                    }}>
                                                        {row.count}
                                                    </span>
                                                </td>
                                                <td style={{
                                                    padding: '16px 24px',
                                                    textAlign: 'right',
                                                    fontSize: '11px',
                                                    color: '#9ca3af',
                                                    fontWeight: '500'
                                                }}>
                                                    {timeAgo(row.last_seen)}
                                                </td>
                                                <td style={{
                                                    padding: '16px 24px',
                                                    textAlign: 'center',
                                                    color: '#9ca3af',
                                                    transition: 'color 0.3s ease',
                                                    cursor: 'pointer'
                                                }}
                                                onMouseEnter={(e) => { e.currentTarget.style.color = '#22d3ee'; }}
                                                onMouseLeave={(e) => { e.currentTarget.style.color = '#9ca3af'; }}
                                                >
                                                    {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                                </td>
                                            </tr>
                                            {isOpen && (
                                                <tr>
                                                    <td colSpan={6} style={{
                                                        padding: '0',
                                                        background: 'rgba(255, 255, 255, 0.01)'
                                                    }}>
                                                        <UserLogs userId={row.user_id} token={token} />
                                                    </td>
                                                </tr>
                                            )}
                                        </React.Fragment>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default DashboardOverview;
