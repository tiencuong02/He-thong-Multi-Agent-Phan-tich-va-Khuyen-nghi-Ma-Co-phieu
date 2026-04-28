import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MessageCircle, X, Bot, TrendingUp, TrendingDown, Sparkles, Send, Trash2, ChevronDown, Copy, Check, AlertTriangle } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const isComparisonQuery = (text) => {
    const lower = text.toLowerCase();
    const hasCompareKeyword = /so\s*sánh|so\s*với|\bvs\b|compare/.test(lower);
    const tickers = text.toUpperCase().match(/\b[A-Z]{2,5}\b/g) || [];
    const STOPWORDS = new Set(['KHÔNG','THEO','TRONG','NĂM','VÀ','CỦA','SO','SÁNH','VỚI','VS','CHO','LÀ','CÓ','BÁO','CÁO','MÃ','CỔ','PHIẾU']);
    const validTickers = [...new Set(tickers.filter(t => !STOPWORDS.has(t)))];
    return hasCompareKeyword && validTickers.length >= 2;
};

const INACTIVITY_WARNING_MS = 5 * 60 * 1000;
const INACTIVITY_TIMEOUT_MS = 10 * 60 * 1000;

const SESSION_END_MESSAGE =
    'Hội thoại đã kết thúc do em không nhận được phản hồi từ Anh/Chị. ' +
    'Vui lòng tham khảo thông tin hỗ trợ về sản phẩm, dịch vụ tại\n' +
    'https://www.fpts.com.vn/ho-tro-khach-hang/giao-dich-chung-khoan/' +
    'huong-dan-giao-dich-co-phieu/huong-dan-mo-tai-khoan/\n' +
    'hoặc tạo lại phiên chat mới để em có thể tiếp tục tư vấn và hỗ trợ. ' +
    'Cảm ơn Anh/Chị đã tin dùng sản phẩm dịch vụ của FPTS.';

const QUICK_CHIPS = [
    { label: '📊 Top mã BUY hôm nay', query: 'Top mã BUY hôm nay' },
    { label: '🔍 Phân tích FPT',       query: 'Phân tích FPT' },
    { label: '🔍 Phân tích VNM',       query: 'Phân tích VNM' },
    { label: '⚖️ So sánh HPG và HSG',  query: 'So sánh HPG và HSG' },
    { label: '📈 Thị trường hôm nay',  query: 'Thị trường hôm nay' },
    { label: '🔍 Phân tích NVDA',      query: 'Phân tích NVDA' },
];

const ChatBotWidget = ({ user }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [hasGreeted, setHasGreeted] = useState(false);
    const [historyLoaded, setHistoryLoaded] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [isSessionEnded, setIsSessionEnded] = useState(false);
    const [showScrollBtn, setShowScrollBtn] = useState(false);
    const [copiedMsgId, setCopiedMsgId] = useState(null);
    const [showConfirmClear, setShowConfirmClear] = useState(false);

    const messagesEndRef = useRef(null);
    const messagesContainerRef = useRef(null);
    const saveTimerRef = useRef(null);
    const abortControllerRef = useRef(null);
    const inactivityWarningRef = useRef(null);
    const inactivityTimeoutRef = useRef(null);

    const sessionIdRef = useRef(
        sessionStorage.getItem('chat_session_id') ||
        (() => {
            const id = typeof crypto !== 'undefined' && crypto.randomUUID
                ? crypto.randomUUID()
                : `sess_${Date.now()}_${Math.random().toString(36).slice(2)}`;
            sessionStorage.setItem('chat_session_id', id);
            return id;
        })()
    );

    const scrollToBottom = (behavior = 'smooth') => {
        messagesEndRef.current?.scrollIntoView({ behavior });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Detect scroll position to show/hide scroll-to-bottom button
    const handleScroll = useCallback(() => {
        const el = messagesContainerRef.current;
        if (!el) return;
        const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        setShowScrollBtn(distanceFromBottom > 120);
    }, []);

    // ─── Inactivity timeout ───────────────────────────────────────────────────
    const clearInactivityTimers = useCallback(() => {
        if (inactivityWarningRef.current) clearTimeout(inactivityWarningRef.current);
        if (inactivityTimeoutRef.current) clearTimeout(inactivityTimeoutRef.current);
    }, []);

    const startInactivityTimer = useCallback(() => {
        clearInactivityTimers();
        if (!isOpen) return;

        inactivityWarningRef.current = setTimeout(() => {
            setMessages(prev => [...prev, {
                id: Date.now(),
                sender: 'bot',
                text: '⏰ Em chưa nhận được phản hồi từ Anh/Chị. Phiên chat sẽ tự động kết thúc sau **5 phút** nữa nếu không có tin nhắn mới.',
                type: 'text',
                data: null,
                sources: [],
                timestamp: new Date(),
                isSystemMsg: true,
            }]);
        }, INACTIVITY_WARNING_MS);

        inactivityTimeoutRef.current = setTimeout(() => {
            setIsSessionEnded(true);
            setMessages(prev => [...prev, {
                id: Date.now(),
                sender: 'bot',
                text: SESSION_END_MESSAGE,
                type: 'text',
                data: null,
                sources: [],
                timestamp: new Date(),
                isSessionEnd: true,
            }]);
        }, INACTIVITY_TIMEOUT_MS);
    }, [isOpen, clearInactivityTimers]);

    const resetInactivityTimer = useCallback(() => {
        if (isSessionEnded) return;
        startInactivityTimer();
    }, [isSessionEnded, startInactivityTimer]);

    useEffect(() => {
        if (isOpen && !isSessionEnded) {
            startInactivityTimer();
        } else {
            clearInactivityTimers();
        }
        return () => clearInactivityTimers();
    }, [isOpen, isSessionEnded, startInactivityTimer, clearInactivityTimers]);

    // Load chat history on mount
    useEffect(() => {
        if (!user || historyLoaded) return;
        const loadHistory = async () => {
            try {
                const token = sessionStorage.getItem('token');
                const res = await axios.get(
                    `${API_BASE_URL}/rag/chat/history?session_id=${sessionIdRef.current}`,
                    { headers: { Authorization: `Bearer ${token}` } }
                );
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
                    setHasGreeted(true);
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
            const token = sessionStorage.getItem('token');
            const chatMessages = msgs
                .filter(m => m.sender === 'user' || m.sender === 'bot')
                .map(m => ({
                    role: m.sender === 'user' ? 'user' : 'assistant',
                    content: typeof m.text === 'string' ? m.text.slice(0, 2000) : ''
                }))
                .filter(m => m.content.length > 0)
                .slice(-50);
            if (chatMessages.length === 0) return;
            await axios.post(`${API_BASE_URL}/rag/chat/save`,
                { session_id: sessionIdRef.current, messages: chatMessages },
                { headers: { Authorization: `Bearer ${token}` } }
            );
        } catch (err) {
            console.warn('ChatBot: Failed to save history', err);
        }
    }, [user]);

    useEffect(() => {
        if (!historyLoaded || messages.length === 0) return;
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        saveTimerRef.current = setTimeout(() => saveChatHistory(messages), 3000);
        return () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current); };
    }, [messages, historyLoaded, saveChatHistory]);

    // Clear chat — xóa session hiện tại + tạo session mới
    const handleClearChat = async () => {
        setShowConfirmClear(false);
        const oldSessionId = sessionIdRef.current;
        const newId = typeof crypto !== 'undefined' && crypto.randomUUID
            ? crypto.randomUUID()
            : `sess_${Date.now()}_${Math.random().toString(36).slice(2)}`;
        sessionIdRef.current = newId;
        sessionStorage.setItem('chat_session_id', newId);

        setMessages([]);
        setIsSessionEnded(false);
        startInactivityTimer();
        try {
            const token = sessionStorage.getItem('token');
            await axios.delete(
                `${API_BASE_URL}/rag/chat/history?session_id=${oldSessionId}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
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
        } catch { /* fallback */ }
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

        addBotMessage(`Chào ${honorific} ${username}! 👋 Tôi là AI Stock Advisor, trợ lý đầu tư cá nhân của ${honorific}.`);

        let featured = null;
        try {
            const token = sessionStorage.getItem('token');
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

            setTimeout(() => {
                addBotMessage(
                    `📊 Dựa trên phong cách đầu tư **${styleLabel}** của ${honorific}, tôi gợi ý mã **${featured.ticker}** — ${reasonPrefix} ${featured.reason}`,
                    'recommendation',
                    featured
                );
            }, 1200);

            setTimeout(() => {
                addBotMessage(`${honorific} có muốn tôi phân tích chi tiết mã **${featured.ticker}** không? Hoặc ${honorific} có thể nhập mã cổ phiếu bất kỳ để tôi phân tích nhé! 🚀`);
            }, 2800);
        } else {
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

    const handleSend = async (overrideText) => {
        const msg = (overrideText || inputValue).trim();
        if (!msg || isTyping || isSessionEnded) return;
        addUserMessage(msg);
        setInputValue('');
        setIsTyping(true);
        resetInactivityTimer();

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        const controller = new AbortController();
        abortControllerRef.current = controller;

        const honorific = getHonorific();
        const token = sessionStorage.getItem('token');

        const recentMessages = [...messages].slice(-10);
        const conversation_history = recentMessages
            .filter(m => m.sender === 'user' || m.sender === 'bot')
            .map(m => ({
                role: m.sender === 'user' ? 'user' : 'assistant',
                content: typeof m.text === 'string' ? m.text.slice(0, 2000) : ''
            }))
            .filter(m => m.content.length > 0);

        try {
            const isComparison = isComparisonQuery(msg);
            const endpoint = isComparison ? '/rag/query/compare/stream' : '/rag/query/stream';

            const res = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ query: msg, conversation_history, session_id: sessionIdRef.current }),
                signal: controller.signal,
            });

            if (!res.ok) {
                if (res.status === 429) {
                    const data = await res.json().catch(() => ({}));
                    addBotMessage(`⚠️ ${data.detail || 'Quá nhiều yêu cầu. Vui lòng thử lại sau.'}`);
                    return;
                }
                throw new Error(`HTTP ${res.status}`);
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let streamedText = '';
            let streamSources = [];
            let streamDisclaimer = '';
            const streamMsgId = Date.now() + Math.random();

            setMessages(prev => [...prev, {
                id: streamMsgId,
                sender: 'bot',
                text: '',
                type: 'text',
                data: null,
                sources: [],
                disclaimer: '',
                timestamp: new Date()
            }]);
            setIsTyping(false);

            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

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
                            if (Array.isArray(parsed.content)) {
                                streamSources = parsed.content;
                            }
                            setMessages(prev => prev.map(m =>
                                m.id === streamMsgId ? { ...m, sources: streamSources } : m
                            ));
                        } else if (parsed.type === 'disclaimer') {
                            streamDisclaimer = parsed.content || '';
                            setMessages(prev => prev.map(m =>
                                m.id === streamMsgId ? { ...m, disclaimer: streamDisclaimer } : m
                            ));
                        } else if (parsed.type === 'error') {
                            streamedText = parsed.content;
                            setMessages(prev => prev.map(m =>
                                m.id === streamMsgId ? { ...m, text: streamedText } : m
                            ));
                        }
                    } catch { /* skip malformed SSE line */ }
                }
            }
            resetInactivityTimer();
        } catch (err) {
            if (err.name === 'AbortError') return;
            console.error('ChatBot Stream Error:', err);
            try {
                const response = await axios.post(`${API_BASE_URL}/rag/query/`,
                    { query: msg, conversation_history },
                    { headers: { Authorization: `Bearer ${token}` } }
                );
                const { answer, sources } = response.data;
                addBotMessage(answer, 'text', null, sources || []);
            } catch {
                addBotMessage(`Xin lỗi ${honorific}, tôi gặp trục trặc khi kết nối. ${honorific} thử lại sau nhé!`);
            }
        } finally {
            setIsTyping(false);
            if (abortControllerRef.current === controller) {
                abortControllerRef.current = null;
            }
        }
    };

    const handleCopyMessage = async (msgId, text) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopiedMsgId(msgId);
            setTimeout(() => setCopiedMsgId(null), 2000);
        } catch {
            /* clipboard not available */
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

        const mdComponents = {
            h2: ({node, ...props}) => <h2 className="chatbot-md-h2" {...props} />,
            h3: ({node, ...props}) => <h3 className="chatbot-md-h3" {...props} />,
            p:  ({node, ...props}) => <p className="mb-2 last:mb-0 break-words" {...props} />,
            ul: ({node, ...props}) => <ul className="list-disc pl-4 mb-2 space-y-1 break-words" {...props} />,
            ol: ({node, ...props}) => <ol className="list-decimal pl-4 mb-2 space-y-1 break-words" {...props} />,
            strong: ({node, ...props}) => <strong className="text-[var(--primary)] font-semibold" {...props} />,
            em: ({node, ...props}) => <em className="chatbot-md-em" {...props} />,
            li: ({node, ...props}) => <li className="mb-1 break-words leading-relaxed" {...props} />,
            hr: ({node, ...props}) => <hr className="chatbot-md-hr" {...props} />,
            pre: ({node, ...props}) => <pre className="whitespace-pre-wrap break-words bg-black/20 p-3 rounded-lg my-2 text-xs font-mono overflow-x-auto border border-white/10 max-w-full" {...props} />,
            code: ({node, inline, ...props}) => inline
                ? <code className="bg-black/30 text-blue-300 px-1.5 py-0.5 rounded text-xs break-words" {...props} />
                : <code className="whitespace-pre-wrap break-words" {...props} />,
            table: ({node, ...props}) => (
                <div className="chatbot-table-wrapper">
                    <table className="chatbot-md-table" {...props} />
                </div>
            ),
            thead: ({node, ...props}) => <thead className="chatbot-md-thead" {...props} />,
            th:    ({node, ...props}) => <th className="chatbot-md-th" {...props} />,
            td:    ({node, ...props}) => <td className="chatbot-md-td" {...props} />,
            tr:    ({node, ...props}) => <tr className="chatbot-md-tr" {...props} />,
        };

        return (
            <>
                <div className="chatbot-markdown-content text-sm leading-relaxed space-y-2">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
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
                {msg.disclaimer && (
                    <div className="chatbot-disclaimer">
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                            {msg.disclaimer}
                        </ReactMarkdown>
                    </div>
                )}
            </>
        );
    };

    // ─── Empty state shown when no messages yet ───────────────────────────────
    const EmptyState = () => (
        <div className="chatbot-empty-state">
            <div className="chatbot-empty-icon">
                <Bot size={36} />
            </div>
            <p className="chatbot-empty-title">AI Stock Advisor</p>
            <p className="chatbot-empty-sub">Hỏi tôi về bất kỳ mã cổ phiếu nào</p>
            <div className="chatbot-empty-hints">
                <span>💡 VD: <em>Phân tích FPT</em></span>
                <span>💡 VD: <em>So sánh VNM và MCH</em></span>
                <span>💡 VD: <em>Top mã BUY hôm nay</em></span>
            </div>
        </div>
    );

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
                                <button
                                    className="chatbot-close"
                                    onClick={() => setShowConfirmClear(true)}
                                    title="Xóa lịch sử chat"
                                >
                                    <Trash2 size={16} />
                                </button>
                            )}
                            <button className="chatbot-close" onClick={() => setIsOpen(false)}>
                                <X size={18} />
                            </button>
                        </div>
                    </div>

                    {/* Confirm clear dialog */}
                    {showConfirmClear && (
                        <div className="chatbot-confirm-bar">
                            <AlertTriangle size={14} className="chatbot-confirm-icon" />
                            <span className="chatbot-confirm-text">Xóa toàn bộ lịch sử chat?</span>
                            <button className="chatbot-confirm-yes" onClick={handleClearChat}>Xóa</button>
                            <button className="chatbot-confirm-no" onClick={() => setShowConfirmClear(false)}>Hủy</button>
                        </div>
                    )}

                    {/* Messages */}
                    <div
                        className="chatbot-messages"
                        ref={messagesContainerRef}
                        onScroll={handleScroll}
                    >
                        {messages.length === 0 && !isTyping && <EmptyState />}

                        {messages.map(msg => (
                            <div key={msg.id} className={`chatbot-msg ${msg.sender}`}>
                                {msg.sender === 'bot' && (
                                    <div className={`chatbot-msg-avatar ${msg.isSystemMsg ? 'warning' : ''}`}>
                                        {msg.isSystemMsg ? <AlertTriangle size={14} /> : <Bot size={14} />}
                                    </div>
                                )}
                                <div className={`chatbot-msg-bubble ${msg.sender}${msg.isSystemMsg ? ' system-warning' : ''}${msg.isSessionEnd ? ' session-end' : ''}`}>
                                    <div className="chatbot-msg-text">
                                        {renderMessage(msg)}
                                    </div>
                                    <div className="chatbot-msg-time">
                                        {formatTime(msg.timestamp)}
                                    </div>
                                    {/* Copy button — chỉ hiện trên bot messages có text */}
                                    {msg.sender === 'bot' && msg.text && !msg.isSystemMsg && (
                                        <button
                                            className="chatbot-copy-btn"
                                            onClick={() => handleCopyMessage(msg.id, msg.text)}
                                            title="Sao chép"
                                        >
                                            {copiedMsgId === msg.id
                                                ? <Check size={12} />
                                                : <Copy size={12} />
                                            }
                                        </button>
                                    )}
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

                    {/* Scroll-to-bottom button */}
                    {showScrollBtn && (
                        <button
                            className="chatbot-scroll-btn"
                            onClick={() => scrollToBottom()}
                            title="Cuộn xuống cuối"
                        >
                            <ChevronDown size={16} />
                        </button>
                    )}

                    {/* Session ended banner */}
                    {isSessionEnded && (
                        <div className="chatbot-session-ended-bar">
                            <span className="chatbot-session-ended-text">Phiên chat đã kết thúc</span>
                            <button className="chatbot-new-session-btn" onClick={handleClearChat}>
                                Tạo phiên mới
                            </button>
                        </div>
                    )}

                    {/* Quick reply chips */}
                    {!isSessionEnded && (
                        <div className="chatbot-chips-row">
                            {QUICK_CHIPS.map((chip) => (
                                <button
                                    key={chip.label}
                                    className="chatbot-chip"
                                    onClick={() => handleSend(chip.query)}
                                    disabled={isTyping}
                                >
                                    {chip.label}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Input */}
                    <div className="chatbot-input-area">
                        <input
                            type="text"
                            className="chatbot-input"
                            placeholder={isSessionEnded ? 'Phiên đã kết thúc — tạo phiên mới để tiếp tục' : 'Nhập mã cổ phiếu (VD: FPT, NVDA)...'}
                            value={inputValue}
                            onChange={(e) => !isSessionEnded && setInputValue(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            disabled={isSessionEnded}
                            style={isSessionEnded ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
                        />
                        <button className="chatbot-send" onClick={() => handleSend()} disabled={!inputValue.trim() || isSessionEnded}>
                            <Send size={16} />
                        </button>
                    </div>
                </div>
            )}
        </>
    );
};

export default ChatBotWidget;
