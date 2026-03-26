import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, X, Bot, TrendingUp, TrendingDown, Sparkles, Send } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const ChatBotWidget = ({ user }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [hasGreeted, setHasGreeted] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Auto-open and greet on first load
    useEffect(() => {
        if (user && !hasGreeted) {
            const timer = setTimeout(() => {
                setIsOpen(true);
                generateGreeting();
                setHasGreeted(true);
            }, 1500); // Small delay for a natural feel
            return () => clearTimeout(timer);
        }
    }, [user, hasGreeted]);

    const getHonorific = () => {
        if (!user) return 'bạn';
        const currentYear = new Date().getFullYear();
        const birthYear = user.dob ? parseInt(user.dob.split('-')[0]) : 1990;
        const age = currentYear - birthYear;
        const gender = user.gender || 'male';

        if (age > 55) return 'Bác';
        if (gender === 'male') return 'Anh';
        if (gender === 'female') return 'Chị';
        return 'bạn';
    };

    const generateGreeting = async () => {
        const honorific = getHonorific();
        const username = user?.username || 'bạn';
        const style = user?.investment_style || 'short_term';

        // First message: greeting
        addBotMessage(`Chào ${honorific} ${username}! 👋 Tôi là AI Stock Advisor, trợ lý đầu tư cá nhân của ${honorific}.`);

        // Prepare fallback data based on style
        const fallbackData = style === 'short_term'
            ? { ticker: 'TSLA', recommendation: 'BUY', reason: 'có biến động giá cao (Volatility) + thanh khoản cực tốt, phù hợp tối ưu lợi nhuận trong vài ngày.' }
            : { ticker: 'FPT', recommendation: 'BUY', reason: 'có nền tảng cơ bản vững chắc và đang trong xu hướng tăng trưởng ổn định, bền vững dài hạn (Long-term trend).' };

        let featured = fallbackData;

        // Try to fetch from API, fallback to hardcoded if fails
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${API_BASE_URL}/stock/featured`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (response.data && response.data.ticker) {
                featured = response.data;
            }
        } catch (err) {
            console.warn('ChatBot: Using fallback featured stock', err);
        }

        const styleLabel = style === 'short_term' ? 'ngắn hạn (Lướt sóng)' : 'dài hạn (Tích sản)';
        const reasonPrefix = style === 'short_term'
            ? 'đang có tiềm năng trading ngắn hạn vì'
            : 'phù hợp chiến lược tích sản dài hạn vì';

        // Second message: stock recommendation (always shown)
        setTimeout(() => {
            addBotMessage(
                `📊 Dựa trên phong cách đầu tư **${styleLabel}** của ${honorific}, tôi gợi ý mã **${featured.ticker}** — ${reasonPrefix} ${featured.reason}`,
                'recommendation',
                featured
            );
        }, 1200);

        // Third message: call to action
        setTimeout(() => {
            addBotMessage(`${honorific} có muốn tôi phân tích chi tiết mã **${featured.ticker}** không? Hoặc ${honorific} có thể nhập mã cổ phiếu bất kỳ để tôi phân tích nhé! 🚀`);
        }, 2800);
    };

    const addBotMessage = (text, type = 'text', data = null) => {
        setMessages(prev => [...prev, {
            id: Date.now() + Math.random(),
            sender: 'bot',
            text,
            type,
            data,
            timestamp: new Date()
        }]);
    };

    const addUserMessage = (text) => {
        setMessages(prev => [...prev, {
            id: Date.now() + Math.random(),
            sender: 'user',
            text,
            timestamp: new Date()
        }]);
    };

    const handleSend = () => {
        if (!inputValue.trim()) return;
        const msg = inputValue.trim();
        addUserMessage(msg);
        setInputValue('');

        const honorific = getHonorific();

        // Simple response logic
        setTimeout(() => {
            if (msg.length <= 5 && msg.toUpperCase() === msg) {
                addBotMessage(`Tốt lắm! ${honorific} muốn phân tích mã **${msg.toUpperCase()}**, hãy nhập mã vào ô tìm kiếm ở trang chính và nhấn "Phân tích" nhé! 📈`);
            } else {
                addBotMessage(`Cảm ơn ${honorific}! Hiện tại tôi có thể giúp ${honorific} gợi ý mã cổ phiếu và phân tích kỹ thuật. Hãy nhập mã cổ phiếu (VD: FPT, NVDA, TSLA) để bắt đầu nhé! 💡`);
            }
        }, 800);
    };

    const formatTime = (date) => {
        return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    };

    const renderMessage = (msg) => {
        if (msg.type === 'recommendation' && msg.data) {
            const rec = msg.data;
            const isBuy = rec.recommendation?.toUpperCase().includes('BUY');
            return (
                <div className="chatbot-rec-card">
                    <div className="chatbot-rec-header">
                        <Sparkles size={14} />
                        <span>GỢI Ý ĐẦU TƯ</span>
                    </div>
                    <div className="chatbot-rec-body">
                        <div className="chatbot-rec-ticker">
                            <span className="chatbot-ticker-name">{rec.ticker}</span>
                            <span className={`chatbot-rec-badge ${isBuy ? 'buy' : 'sell'}`}>
                                {isBuy ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                                {rec.recommendation}
                            </span>
                        </div>
                        <p className="chatbot-rec-reason">{rec.reason}</p>
                    </div>
                </div>
            );
        }

        // Parse **bold** in text
        const parts = msg.text.split(/(\*\*[^*]+\*\*)/g);
        return parts.map((part, i) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                return <strong key={i} style={{ color: 'var(--primary)' }}>{part.slice(2, -2)}</strong>;
            }
            return part;
        });
    };

    return (
        <>
            {/* Floating Chat Button */}
            {!isOpen && (
                <button
                    className="chatbot-fab"
                    onClick={() => setIsOpen(true)}
                    title="Mở trợ lý AI"
                >
                    <MessageCircle size={24} />
                    {messages.length > 0 && <span className="chatbot-fab-dot" />}
                </button>
            )}

            {/* Chat Window */}
            {isOpen && (
                <div className="chatbot-window">
                    {/* Header */}
                    <div className="chatbot-header">
                        <div className="chatbot-header-info">
                            <div className="chatbot-avatar">
                                <Bot size={20} />
                            </div>
                            <div>
                                <div className="chatbot-name">AI Stock Advisor</div>
                                <div className="chatbot-status">
                                    <span className="chatbot-status-dot" />
                                    Đang hoạt động
                                </div>
                            </div>
                        </div>
                        <button className="chatbot-close" onClick={() => setIsOpen(false)}>
                            <X size={18} />
                        </button>
                    </div>

                    {/* Messages */}
                    <div className="chatbot-messages">
                        {messages.map(msg => (
                            <div key={msg.id} className={`chatbot-msg ${msg.sender}`}>
                                {msg.sender === 'bot' && (
                                    <div className="chatbot-msg-avatar">
                                        <Bot size={14} />
                                    </div>
                                )}
                                <div className={`chatbot-msg-bubble ${msg.sender}`}>
                                    <div className="chatbot-msg-text">
                                        {renderMessage(msg)}
                                    </div>
                                    <div className="chatbot-msg-time">
                                        {formatTime(msg.timestamp)}
                                    </div>
                                </div>
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div className="chatbot-input-area">
                        <input
                            type="text"
                            className="chatbot-input"
                            placeholder="Nhập mã cổ phiếu (VD: FPT, NVDA)..."
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        />
                        <button className="chatbot-send" onClick={handleSend} disabled={!inputValue.trim()}>
                            <Send size={16} />
                        </button>
                    </div>
                </div>
            )}
        </>
    );
};

export default ChatBotWidget;
