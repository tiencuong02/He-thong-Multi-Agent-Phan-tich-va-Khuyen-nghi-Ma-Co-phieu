import React from 'react';
import { Search, RefreshCw } from 'lucide-react';

const SearchBar = ({ ticker, setTicker, handleAnalyze, loading }) => {
    return (
        <form onSubmit={handleAnalyze} className="search-group fade-in">
            <div className="input-wrapper">
                <Search className="search-icon" size={24} />
                <input
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value.toUpperCase())}
                    placeholder="Nhập mã cổ phiếu (ví dụ: VNM, FPT...)"
                />
            </div>
            <button disabled={loading} type="submit" className="btn-primary">
                {loading ? <RefreshCw className="animate-spin" /> : 'Phân tích'}
            </button>
        </form>
    );
};

export default SearchBar;
