import React, { useState } from 'react';

const Dashboard = () => {
  const [ticker, setTicker] = useState('');

  const handleAnalyze = () => {
    console.log(`Analyzing ${ticker}`);
    // Call backend POST /analyze
  };

  return (
    <div>
      <h1>Stock Analysis Dashboard</h1>
      <input 
        type="text" 
        value={ticker} 
        onChange={(e) => setTicker(e.target.value)} 
        placeholder="Enter Ticker (e.g. AAPL)"
      />
      <button onClick={handleAnalyze}>Analyze</button>
    </div>
  );
};

export default Dashboard;
