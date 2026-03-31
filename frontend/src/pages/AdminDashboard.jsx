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
  const location = useLocation();

  // Determine page title based on path
  const getPageTitle = (path) => {
    if (path === '/admin') return 'Dashboard Overview';
    if (path === '/admin/knowledge-base') return 'Knowledge Base';
    if (path === '/admin/quotes') return 'Quote Management';
    if (path === '/admin/stats') return 'Data Statistics';
    return 'Admin Panel';
  };

  return (
    <div className="admin-layout">
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />

      <main className={`admin-main ${collapsed ? 'expanded' : ''}`}>
        <AdminNavbar title={getPageTitle(location.pathname)} />

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
