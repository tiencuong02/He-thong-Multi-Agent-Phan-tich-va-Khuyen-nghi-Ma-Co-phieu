import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

const StatCard = ({ title, value, icon: Icon, trend, trendValue, description }) => {
  const isPositive = trend === 'up';

  return (
    <div className="stat-card">
      <div className="stat-header">
        <span className="stat-label">{title}</span>
        <div className="stat-icon">
          <Icon size={18} />
        </div>
      </div>

      <div className="stat-value">{value}</div>

      {(trendValue || description) && (
        <div className="stat-trend">
          {trendValue && (
            <span className={isPositive ? 'trend-up' : 'trend-down'}>
              {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {trendValue}
            </span>
          )}
          <span className="text-gray-500 ml-1">{description}</span>
        </div>
      )}
    </div>
  );
};

export default StatCard;
