import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Quote as QuoteIcon, 
  BarChart3,
  BookOpen,
  Settings, 
  Menu, 
  ChevronLeft 
} from 'lucide-react';

const Sidebar = ({ collapsed, setCollapsed, mobileOpen, setMobileOpen }) => {
  const navItems = [
    { path: '/admin', icon: LayoutDashboard, label: 'Overview', end: true },
    { path: '/admin/knowledge-base', icon: BookOpen, label: 'Knowledge Base' },
    { path: '/admin/quotes', icon: QuoteIcon, label: 'Quotes' },
    { path: '/admin/stats', icon: BarChart3, label: 'Statistics' },
  ];

  const handleNavClick = () => {
    if (mobileOpen) setMobileOpen(false);
  };

  return (
    <aside className={`admin-sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="sidebar-brand">
        <div className="stat-icon">
          <LayoutDashboard size={24} />
        </div>
        {!collapsed && <span className="brand-text">Admin Panel</span>}
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className="ml-auto p-1.5 hover:bg-white/5 rounded-lg text-gray-400"
        >
          {collapsed ? <Menu size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.end}
            onClick={handleNavClick}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            {({ isActive }) => (
              <>
                <item.icon size={22} strokeWidth={isActive ? 2.5 : 2} />
                {!collapsed && <span>{item.label}</span>}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <NavLink to="/admin/settings" onClick={handleNavClick} className="nav-link">
          <Settings size={22} />
          {!collapsed && <span>Settings</span>}
        </NavLink>
      </div>
    </aside>
  );
};

export default Sidebar;
