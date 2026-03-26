import React, { useState } from 'react';
import { X, Save, User as UserIcon } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const ProfileModal = ({ user, onClose, onUpdate }) => {
    const [activeTab, setActiveTab] = useState('info'); // 'info' or 'config'
    const [formData, setFormData] = useState({
        gender: user.gender || 'male',
        dob: user.dob || '1990-01-01',
        investment_style: user.investment_style || 'short_term'
    });
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        const token = localStorage.getItem('token');
        try {
            await axios.put(`${API_BASE_URL}/auth/profile`, formData, {
                headers: { Authorization: `Bearer ${token}` }
            });
            onUpdate();
            onClose();
        } catch (err) {
            console.error('Failed to update profile', err);
            alert('Lỗi khi cập nhật hồ sơ');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="modal-overlay fade-in">
            <div className="glass-card modal-content" style={{ maxWidth: '500px', width: '90%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <UserIcon className="opportunity-text" />
                        <h3 style={{ margin: 0 }}>Cấu hình hồ sơ cá nhân</h3>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                        <X size={24} />
                    </button>
                </div>

                <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', marginBottom: '2rem' }}>
                    <button 
                        onClick={() => setActiveTab('info')}
                        style={{ 
                            padding: '0.75rem 1rem', 
                            background: 'none', 
                            border: 'none', 
                            borderBottom: activeTab === 'info' ? '2px solid var(--primary)' : '2px solid transparent',
                            color: activeTab === 'info' ? 'var(--primary)' : 'var(--text-muted)',
                            cursor: 'pointer',
                            fontWeight: '600',
                            fontSize: '0.9rem'
                        }}
                    >
                        Thông tin cá nhân
                    </button>
                    <button 
                        onClick={() => setActiveTab('config')}
                        style={{ 
                            padding: '0.75rem 1rem', 
                            background: 'none', 
                            border: 'none', 
                            borderBottom: activeTab === 'config' ? '2px solid var(--primary)' : '2px solid transparent',
                            color: activeTab === 'config' ? 'var(--primary)' : 'var(--text-muted)',
                            cursor: 'pointer',
                            fontWeight: '600',
                            fontSize: '0.9rem'
                        }}
                    >
                        Cấu hình cá nhân
                    </button>
                </div>

                {activeTab === 'info' ? (
                    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1.5rem', borderRadius: '1rem', border: '1px solid rgba(255,255,255,0.05)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Tên đăng nhập</span>
                                <span style={{ fontWeight: '700' }}>{user.username}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>
                                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Vai trò</span>
                                <span style={{ color: 'var(--primary)', fontWeight: '700' }}>{user.role === 'ADMIN' ? 'Quản trị viên' : 'Nhà đầu tư'}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Trạng thái</span>
                                <span style={{ color: 'var(--secondary)', fontWeight: '700' }}>● Đang hoạt động</span>
                            </div>
                        </div>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', fontStyle: 'italic' }}>
                            Thông tin đăng nhập không thể thay đổi từ phía người dùng.
                        </p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Xưng hô (Giới tính)</label>
                            <select 
                                value={formData.gender} 
                                onChange={(e) => setFormData({...formData, gender: e.target.value})}
                                style={{ 
                                    width: '100%', 
                                    padding: '0.75rem', 
                                    background: 'rgba(255,255,255,0.05)', 
                                    border: '1px solid rgba(255,255,255,0.1)', 
                                    borderRadius: '0.5rem', 
                                    color: 'white', 
                                    outline: 'none',
                                    appearance: 'none',
                                    backgroundImage: `url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e")`,
                                    backgroundRepeat: 'no-repeat',
                                    backgroundPosition: 'right 1rem center',
                                    backgroundSize: '1em'
                                }}
                            >
                                <option value="male" style={{ background: '#1e293b', color: 'white' }}>Nam</option>
                                <option value="female" style={{ background: '#1e293b', color: 'white' }}>Nữ</option>
                                <option value="other" style={{ background: '#1e293b', color: 'white' }}>Khác</option>
                            </select>
                        </div>

                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Ngày sinh</label>
                            <input 
                                type="date" 
                                value={formData.dob} 
                                onChange={(e) => setFormData({...formData, dob: e.target.value})}
                                style={{ 
                                    width: '100%', 
                                    padding: '0.75rem', 
                                    background: 'rgba(255,255,255,0.05)', 
                                    border: '1px solid rgba(255,255,255,0.1)', 
                                    borderRadius: '0.5rem', 
                                    color: 'white', 
                                    outline: 'none',
                                    colorScheme: 'dark' 
                                }}
                            />
                        </div>

                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Trường phái đầu tư</label>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                                <button 
                                    type="button"
                                    onClick={() => setFormData({...formData, investment_style: 'short_term'})}
                                    style={{ 
                                        padding: '1rem', 
                                        borderRadius: '0.75rem', 
                                        border: `1px solid ${formData.investment_style === 'short_term' ? 'var(--primary)' : 'rgba(255,255,255,0.1)'}`,
                                        background: formData.investment_style === 'short_term' ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
                                        color: formData.investment_style === 'short_term' ? 'var(--primary)' : 'var(--text-muted)',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease'
                                    }}
                                >
                                    Ngắn hạn (Lướt sóng)
                                </button>
                                <button 
                                    type="button"
                                    onClick={() => setFormData({...formData, investment_style: 'long_term'})}
                                    style={{ 
                                        padding: '1rem', 
                                        borderRadius: '0.75rem', 
                                        border: `1px solid ${formData.investment_style === 'long_term' ? 'var(--secondary)' : 'rgba(255,255,255,0.1)'}`,
                                        background: formData.investment_style === 'long_term' ? 'rgba(16, 185, 129, 0.1)' : 'transparent',
                                        color: formData.investment_style === 'long_term' ? 'var(--secondary)' : 'var(--text-muted)',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease'
                                    }}
                                >
                                    Dài hạn (Tích sản)
                                </button>
                            </div>
                        </div>

                        <button 
                            type="submit" 
                            disabled={loading}
                            style={{ 
                                marginTop: '1rem',
                                padding: '1rem', 
                                background: 'linear-gradient(135deg, var(--primary), var(--accent))', 
                                border: 'none', 
                                borderRadius: '0.75rem', 
                                color: 'white', 
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.5rem',
                                transition: 'all 0.3s ease'
                            }}
                        >
                            <Save size={18} /> {loading ? 'Đang lưu...' : 'Lưu cấu hình'}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
};

export default ProfileModal;
