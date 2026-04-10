import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MessageCircle, X, Bot, TrendingUp, TrendingDown, Sparkles, Send, Trash2 } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const ChatBotWidget = ({ user }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [hasGreeted, setHasGreeted] = useState(false);
    const [historyLoaded, setHistoryLoaded] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef(null);
    const saveTimerRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Load chat history on mount
    useEffect(() => {
        if (!user || historyLoaded) return;
        const loadHistory = async () => {
            try {
                const token = localStorage.getItem('token');
                const res = await axios.get(`${API_BASE_URL}/rag/chat/history`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (res.data?.messages?.length > 0) {
                    const restored = res.data.messages.map((m, i) => ({
                        id: Date.now() + i,
                        sender: m.role === 'user' ? 'user' : 'bot',
                        text: m.content,
                        type: 'text',
                        data: null,
                        sources: [],
                        timestamp: new Date()
                    }));
                    setMessages(restored);
                    setHasGreeted(true); // Skip greeting if history exists
                }
            } catch (err) {
                console.warn('ChatBot: Failed to load history', err);
            } finally {
                setHistoryLoaded(true);
            }
        };
        loadHistory();
    }, [user, historyLoaded]);

    // Auto-save chat history (debounced)
    const saveChatHistory = useCallback(async (msgs) => {
        if (!user || msgs.length === 0) return;
        try {
            const token = localStorage.getItem('token');
            const chatMessages = msgs
                .filter(m => m.sender === 'user' || m.sender === 'bot')
                .map(m => ({
                    role: m.sender === 'user' ? 'user' : 'assistant',
                    content: typeof m.text === 'string' ? m.text.slice(0, 2000) : ''
                }))
                .filter(m => m.content.length > 0)
                .slice(-50); // Keep last 50 messages max
            if (chatMessages.length === 0) return;
            await axios.post(`${API_BASE_URL}/rag/chat/save`,
                { messages: chatMessages },
                { headers: { Authorization: `Bearer ${token}` } }
            );
        } catch (err) {
            console.warn('ChatBot: Failed to save history', err);
        }
    }, [user]);

    // Debounced auto-save when messages change
    useEffect(() => {
        if (!historyLoaded || messages.length === 0) return;
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        saveTimerRef.current = setTimeout(() => saveChatHistory(messages), 3000);
        return () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current); };
    }, [messages, historyLoaded, saveChatHistory]);

    // Clear chat handler
    const handleClearChat = async () => {
        setMessages([]);
        try {
            const token = localStorage.getItem('token');
            await axios.delete(`${API_BASE_URL}/rag/chat/history`, {
                headers: { Authorization: `Bearer ${token}` }
            });
        } catch (err) {
            console.warn('ChatBot: Failed to clear history', err);
        }
    };

    // Auto-open and greet on first load
    useEffect(() => {
        if (user && !hasGreeted && historyLoaded) {
            const timer = setTimeout(() => {
                setIsOpen(true);
                generateGreeting();
                setHasGreeted(true);
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [user, hasGreeted, historyLoaded]);

    const getHonorific = () => {
        if (!user) return 'bạn';
        const currentYear = new Date().getFullYear();
        let birthYear = 1990;
        try {
            if (user.dob && typeof user.dob === 'string') {
                const parsed = parseInt(user.dob.split('-')[0]);
                if (!isNaN(parsed) && parsed > 1900 && parsed <= currentYear) {
                    birthYear = parsed;
                }
            }
        } catch { /* fallback to default */ }
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

        let featured = null;

        // Try to fetch from API
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${API_BASE_URL}/stock/featured/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (response.data && response.data.ticker) {
                featured = response.data;
            }
        } catch (err) {
            console.warn('ChatBot: Failed to fetch featured stock', err);
        }

        if (featured) {
            const styleLabel = style === 'short_term' ? 'ngắn hạn (Lướt sóng)' : 'dài hạn (Tích sản)';
            const reasonPrefix = style === 'short_term'
                ? 'đang có tiềm năng trading ngắn hạn vì'
                : 'phù hợp chiến lược tích sản dài hạn vì';

            // Second message: stock recommendation
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
        } else {
            // No featured stock found (no BUY signals in market or DB)
            setTimeout(() => {
                addBotMessage(`Hiện tại hệ thống đang quét thị trường và chưa có mã cổ phiếu nào đạt điểm **MUA** tự động. ${honorific} có muốn tôi phân tích chi tiết một mã cổ phiếu cụ thể nào không? 🚀`);
            }, 1200);
        }
    };

    const addBotMessage = (text, type = 'text', data = null, sources = []) => {
        setMessages(prev => [...prev, {
            id: Date.now() + Math.random(),
            sender: 'bot',
            text,
            type,
            data,
            sources,
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

    const handleSend = async () => {
        if (!inputValue.trim() || isTyping) return;
        const msg = inputValue.trim();
        addUserMessage(msg);
        setInputValue('');
        setIsTyping(true);

        const honorific = getHonorific();
        const token = localStorage.getItem('token');

        // Build conversation history from recent messages (max 10)
        const recentMessages = [...messages].slice(-10);
        const conversation_history = recentMessages
            .filter(m => m.sender === 'user' || m.sender === 'bot')
            .map(m => ({
                role: m.sender === 'user' ? 'user' : 'assistant',
                content: typeof m.text === 'string' ? m.text.slice(0, 2000) : ''
            }))
            .filter(m => m.content.length > 0);

        try {
            // Streaming request via fetch + SSE
            const res = await fetch(`${API_BASE_URL}/rag/query/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ query: msg, conversation_history })
            });

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let streamedText = '';
            let streamSources = [];
            const streamMsgId = Date.now() + Math.random();

            // Add empty bot message that will be updated with streamed content
            setMessages(prev => [...prev, {
                id: streamMsgId,
                sender: 'bot',
                text: '',
                type: 'text',
                data: null,
                sources: [],
                timestamp: new Date()
            }]);
            setIsTyping(false); // Hide typing indicator, show streaming message

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value, { stream: true });
                const lines = text.split('\n');

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = line.slice(6).trim();
                    if (data === '[DONE]') break;

                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.type === 'token') {
                            streamedText += parsed.content;
                            setMessages(prev => prev.map(m =>
                                m.id === streamMsgId ? { ...m, text: streamedText } : m
                            ));
                        } else if (parsed.type === 'sources') {
                            streamSources = parsed.content;
                            setMessages(prev => prev.map(m =>
                                m.id === streamMsgId ? { ...m, sources: streamSources } : m
                            ));
                        } else if (parsed.type === 'error') {
                            streamedText += `\n\n❌ Lỗi: ${parsed.content}`;
                            setMessages(prev => prev.map(m =>
                                m.id === streamMsgId ? { ...m, text: streamedText } : m
                            ));
                        }
                    } catch { /* skip malformed SSE line */ }
                }
            }
        } catch (err) {
            console.error('ChatBot Stream Error:', err);
            // Fallback to non-streaming if stream fails
            try {
                const response = await axios.post(`${API_BASE_URL}/rag/query/`,
                    { query: msg, conversation_history },
                    { headers: { Authorization: `Bearer ${token}` } }
                );
                const { answer, sources } = response.data;
                addBotMessage(answer, 'text', null, sources || []);
            } catch (fallbackErr) {
                addBotMessage(`Xin lỗi ${honorific}, tôi gặp trục trặc khi kết nối. ${honorific} thử lại sau nhé!`);
            }
        } finally {
            setIsTyping(false);
        }
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

        return (
            <>
                <div className="chatbot-markdown-content text-sm leading-relaxed space-y-2">
                    <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                            h3: ({node, ...props}) => <h3 className="text-sm font-bold mt-2 mb-1" {...props} />,
                            p: ({node, ...props}) => <p className="mb-2 last:mb-0 break-words" {...props} />,
                            ul: ({node, ...props}) => <ul className="list-disc pl-4 mb-2 space-y-1 break-words" {...props} />,
                            ol: ({node, ...props}) => <ol className="list-decimal pl-4 mb-2 space-y-1 break-words" {...props} />,
                            strong: ({node, ...props}) => <strong className="text-[var(--primary)] font-semibold" {...props} />,
                            li: ({node, ...props}) => <li className="mb-1 break-words leading-relaxed" {...props} />,
                            pre: ({node, ...props}) => <pre className="whitespace-pre-wrap break-words bg-black/20 p-3 rounded-lg my-2 text-xs font-mono overflow-x-auto border border-white/10 max-w-full" {...props} />,
                            code: ({node, inline, ...props}) => inline ? <code className="bg-black/30 text-blue-300 px-1.5 py-0.5 rounded text-xs break-words" {...props} /> : <code className="whitespace-pre-wrap break-words" {...props} />
                        }}
                    >
                        {msg.text}
                    </ReactMarkdown>
                </div>
                {msg.sources && msg.sources.length > 0 && (
                    <div className="chatbot-sources">
                        <div className="chatbot-sources-title">Nguồn trích dẫn:</div>
                        <ul className="chatbot-sources-list">
                            {msg.sources.map((s, idx) => (
                                <li key={idx} className="chatbot-source-item">
                                    📄 {s.doc_type || 'Báo cáo'}: {s.source} {s.page ? `(Trang ${s.page})` : ''} 
                                    {s.period && <span className="chatbot-source-period"> - {s.period}</span>}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </>
        );
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
                        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                            {messages.length > 0 && (
                                <button className="chatbot-close" onClick={handleClearChat} title="Xóa lịch sử chat">
                                    <Trash2 size={16} />
                                </button>
                            )}
                            <button className="chatbot-close" onClick={() => setIsOpen(false)}>
                                <X size={18} />
                            </button>
                        </div>
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
                        {isTyping && (
                            <div className="chatbot-msg bot">
                                <div className="chatbot-msg-avatar">
                                    <Bot size={14} />
                                </div>
                                <div className="chatbot-msg-bubble bot typing">
                                    <div className="chatbot-typing-dots">
                                        <span></span><span></span><span></span>
                                    </div>
                                </div>
                            </div>
                        )}
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
