import React, { useState } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Sidebar from '../components/admin/Sidebar';
import AdminNavbar from '../components/admin/AdminNavbar';
import DashboardOverview from '../components/admin/DashboardOverview';
import QuoteManagement from '../components/admin/QuoteManagement';
import QuoteStats from '../components/admin/QuoteStats';
import KnowledgeBase from '../components/admin/KnowledgeBase';

const AdminDashboard = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const getPageTitle = (path) => {
    if (path === '/admin') return 'Dashboard Overview';
    if (path === '/admin/knowledge-base') return 'Knowledge Base';
    if (path === '/admin/quotes') return 'Quote Management';
    if (path === '/admin/stats') return 'Data Statistics';
    return 'Admin Panel';
  };

  return (
    <div className="admin-layout">
      {mobileOpen && (
        <div
          className="admin-mobile-backdrop"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <Sidebar
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
      />

      <main className={`admin-main ${collapsed ? 'expanded' : ''}`}>
        <AdminNavbar
          title={getPageTitle(location.pathname)}
          onMobileMenuToggle={() => setMobileOpen(!mobileOpen)}
        />

        <div className="content-container">
          <Routes>
            <Route index element={<DashboardOverview />} />
            <Route path="knowledge-base" element={<KnowledgeBase />} />
            <Route path="quotes" element={<QuoteManagement />} />
            <Route path="stats" element={<QuoteStats />} />
          </Routes>
        </div>
      </main>
    </div>
  );
};

export default AdminDashboard;
