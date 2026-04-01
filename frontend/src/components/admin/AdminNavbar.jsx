import React from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, User, Bell, Home } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const AdminNavbar = ({ title }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="admin-navbar">
      <div className="nav-title">{title}</div>

      <div className="nav-profile">
        {/* Back to User Dashboard */}
        <button
          onClick={() => navigate('/')}
          className="profile-btn mr-2"
          title="Về màn hình phân tích"
        >
          <Home size={18} />
          <span className="hidden sm:inline">Quay lại</span>
        </button>

        <button className="p-2 text-gray-400 hover:text-white transition-colors relative">
          <Bell size={20} />
          <span className="absolute top-2 right-2 w-2 h-2 bg-blue-500 rounded-full border-2 border-[#020617]" />
        </button>

        <div className="h-8 w-[1px] bg-white/5 mx-2" />

        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <div className="text-sm font-semibold text-white">{user?.username || 'Admin User'}</div>
            <div className="user-badge">{user?.role || 'ADMIN'}</div>
          </div>
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center border border-white/10">
            <User size={20} className="text-white" />
          </div>
        </div>

        <button
          onClick={handleLogout}
          className="ml-4 p-2 text-red-400 hover:bg-red-400/10 rounded-lg transition-all group"
          title="Logout"
        >
          <LogOut size={20} className="group-hover:scale-110 transition-transform" />
        </button>
      </div>
    </nav>
  );
};

export default AdminNavbar;
