import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Upload, FileText, CheckCircle2, AlertCircle, RefreshCw,
  Trash2, BookOpen, Database, ArrowRightLeft, X, Loader2
} from 'lucide-react';
import './KnowledgeBase.css';

const DOC_TYPE_OPTIONS = ["Báo cáo tài chính", "Báo cáo thường niên", "Báo cáo phân tích", "Nghị quyết ĐHCĐ", "Tin tức doanh nghiệp", "Cẩm nang đầu tư", "Khác"];
const PERIOD_OPTIONS = ["Cả năm", "Quý 1", "Quý 2", "Quý 3", "Quý 4", "6 tháng đầu năm", "9 tháng"];
const NAMESPACE_OPTIONS = [
  { id: 'advisory', name: 'Tư vấn đầu tư', color: '#3b82f6' },
  { id: 'knowledge', name: 'Kiến thức chung', color: '#10b981' },
  { id: 'faq', name: 'FAQ & Hỗ trợ', color: '#f59e0b' }
];

const KnowledgeBase = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [ticker, setTicker] = useState('');
  const [docType, setDocType] = useState(DOC_TYPE_OPTIONS[0]);
  const [namespaceType, setNamespaceType] = useState('advisory');
  const [period, setPeriod] = useState(PERIOD_OPTIONS[0]);
  const [year, setYear] = useState(new Date().getFullYear().toString());
  const [uploadResult, setUploadResult] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [reindexTarget, setReindexTarget] = useState(null);
  const [reindexing, setReindexing] = useState(null);
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0 });
  const fileInputRef = useRef(null);
  const pollRef = useRef(null);
  const fetchRef = useRef(null);

  const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

  const fetchDocuments = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const token = sessionStorage.getItem('token');
      const res = await axios.get(`${API_URL}/rag/documents/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDocuments(res.data);
      const hasProcessing = res.data.some(d => !d.status || d.status === 'processing');
      if (hasProcessing && !pollRef.current) {
        pollRef.current = setInterval(() => fetchRef.current(true), 5000);
      } else if (!hasProcessing && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch (err) {
      console.error("Fetch docs failed", err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  fetchRef.current = fetchDocuments;

  useEffect(() => {
    fetchDocuments();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  useEffect(() => {
    if (!reindexTarget) return;
    const close = (e) => {
      if (!e.target.closest('.kb-reindex-btn') && !e.target.closest('.kb-reindex-menu')) {
        setReindexTarget(null);
      }
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [reindexTarget]);

  const getStatusBadge = (status) => {
    if (status === 'indexed') {
      return (
        <span className="kb-status-badge kb-status-indexed">
          <CheckCircle2 size={11} /> Đã index
        </span>
      );
    }
    if (status === 'error') {
      return (
        <span className="kb-status-badge kb-status-error">
          <AlertCircle size={11} /> Lỗi
        </span>
      );
    }
    return (
      <span className="kb-status-badge kb-status-processing">
        <Loader2 size={11} className="kb-spin" /> Đang xử lý
      </span>
    );
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadResult(null);
    }
  };

  // Ticker chỉ bắt buộc với namespace advisory (tài liệu gắn với mã cổ phiếu cụ thể)
  const tickerRequired = namespaceType === 'advisory';
  const effectiveTicker = tickerRequired ? ticker : (ticker.trim() || 'GENERAL');

  const handleUpload = async () => {
    if (!selectedFile) return;
    if (tickerRequired && !ticker.trim()) return;
    setUploading(true);
    const token = sessionStorage.getItem('token');
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('ticker', effectiveTicker);
    formData.append('doc_type', docType);
    formData.append('namespace_type', namespaceType);
    formData.append('period', period);
    formData.append('year', year);

    try {
      const res = await axios.post(`${API_URL}/rag/upload/`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          Authorization: `Bearer ${token}` 
        }
      });
      setUploadResult({ type: 'success', message: res.data.message });
      setSelectedFile(null);
      setTicker('');
      fetchDocuments();
    } catch (err) {
      setUploadResult({ 
        type: 'error', 
        message: err.response?.data?.detail || "Upload thất bại." 
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    try {
      const token = sessionStorage.getItem('token');
      await axios.delete(`${API_URL}/rag/documents/${docId}/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDocuments(documents.filter(d => d._id !== docId));
      setDeleteConfirm(null);
    } catch (err) {
      alert("Xóa thất bại");
    }
  };

  const handleReindex = async (docId, targetNs) => {
    setReindexing(docId);
    setReindexTarget(null);
    try {
      const token = sessionStorage.getItem('token');
      const formData = new FormData();
      formData.append('target_namespace_type', targetNs);
      const res = await axios.post(`${API_URL}/rag/documents/${docId}/reindex`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUploadResult({ type: 'success', message: res.data.message || 'Chuyển ngăn thành công!' });
      fetchDocuments();
    } catch (err) {
      setUploadResult({ type: 'error', message: err.response?.data?.detail || 'Chuyển ngăn thất bại.' });
    } finally {
      setReindexing(null);
    }
  };

  const getNamespaceBadge = (ns) => {
    const option = NAMESPACE_OPTIONS.find(opt => ns?.includes(opt.id)) || NAMESPACE_OPTIONS[0];
    return (
      <span className="kb-ns-badge" style={{ backgroundColor: option.color + '20', color: option.color }}>
        <Database size={10} />
        {option.name}
      </span>
    );
  };

  return (
    <div className="kb-container">
      <div className="kb-header">
        <h2>Knowledge Base Manager</h2>
        <p>Quản lý tài liệu đa ngăn chứa cho AI</p>
      </div>

      <div className="kb-upload-card">
        <div 
          className="kb-dropzone"
          onClick={() => fileInputRef.current?.click()}
        >
          <input 
            ref={fileInputRef} 
            type="file" 
            accept=".pdf" 
            onChange={handleFileSelect} 
            style={{ display: 'none' }} 
          />
          {selectedFile ? (
            <div className="kb-file-info">
              <FileText size={32} className="text-cyan-400" />
              <span className="kb-filename">{selectedFile.name}</span>
              <button className="kb-remove-file" onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}><X size={16} /></button>
            </div>
          ) : (
            <div className="kb-drop-placeholder">
              <Upload size={40} strokeWidth={1.5} />
              <p>Nhấp hoặc kéo thả file PDF vào đây</p>
            </div>
          )}
        </div>

        <div className="kb-form-grid">
          <div className="kb-form-group">
            <label>
              Mã cổ phiếu {tickerRequired ? '*' : <span style={{ color: '#6b7280', fontWeight: 400 }}>(tuỳ chọn)</span>}
            </label>
            <input
              type="text"
              value={ticker}
              onChange={e => setTicker(e.target.value.toUpperCase())}
              className="kb-input"
              placeholder={tickerRequired ? 'VD: FPT, VNM...' : 'Bỏ trống nếu là tài liệu chung'}
            />
            {!tickerRequired && (
              <small style={{ color: '#6b7280', marginTop: 4, display: 'block' }}>
                Tài liệu chung sẽ được gắn mã <code>GENERAL</code> tự động
              </small>
            )}
          </div>
          <div className="kb-form-group">
            <label>Ngăn chứa</label>
            <select value={namespaceType} onChange={e => setNamespaceType(e.target.value)} className="kb-input">
              {NAMESPACE_OPTIONS.map(opt => <option key={opt.id} value={opt.id}>{opt.name}</option>)}
            </select>
          </div>
          <div className="kb-form-group">
            <label>Loại tài liệu</label>
            <select value={docType} onChange={e => setDocType(e.target.value)} className="kb-input">
              {DOC_TYPE_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
          <div className="kb-form-group">
            <label>Kỳ báo cáo</label>
            <select value={period} onChange={e => setPeriod(e.target.value)} className="kb-input">
              {PERIOD_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
          <div className="kb-form-group">
            <label>Năm</label>
            <input 
              type="text" 
              value={year} 
              onChange={e => setYear(e.target.value)} 
              className="kb-input" 
              placeholder="VD: 2024"
              maxLength={4}
            />
          </div>
        </div>

        <button className="kb-upload-btn" onClick={handleUpload} disabled={uploading || !selectedFile || (tickerRequired && !ticker.trim())}>
          {uploading ? <><RefreshCw size={16} className="kb-spin" /> Đang xử lý...</> : <><Upload size={16} /> Upload & Index</>}
        </button>
        {uploadResult && <div className={`kb-alert ${uploadResult.type}`}><span>{uploadResult.message}</span></div>}
      </div>

      <div className="kb-docs-section">
        <h3><BookOpen size={18} /> Danh sách tài liệu ({documents.length})</h3>
        <div className="kb-table-wrapper">
          <table className="kb-table">
            <thead>
              <tr><th>File</th><th>Mã</th><th>Ngăn chứa</th><th>Loại</th><th>Kỳ/Năm</th><th>Ngày</th><th>Trạng thái</th><th>Thao tác</th></tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc._id}>
                  <td className="kb-td-filename" title={doc.filename}><FileText size={14} /> <span>{doc.filename}</span></td>
                  <td><span className="kb-ticker-badge">{doc.ticker}</span></td>
                  <td>{getNamespaceBadge(doc.namespace || doc.pinecone_namespace || doc.namespace_type)}</td>
                  <td>{doc.doc_type}</td>
                  <td>{doc.period} {doc.year}</td>
                  <td>{new Date(doc.uploaded_at).toLocaleDateString()}</td>
                  <td>{getStatusBadge(doc.status)}</td>
                  <td className="kb-actions">
                    <button
                      className={`kb-reindex-btn ${reindexTarget === doc._id ? 'kb-reindex-active' : ''}`}
                      title="Chuyển ngăn chứa"
                      disabled={reindexing === doc._id}
                      onClick={(e) => {
                        setDeleteConfirm(null);
                        if (reindexTarget === doc._id) {
                          setReindexTarget(null);
                        } else {
                          const rect = e.currentTarget.getBoundingClientRect();
                          setDropdownPos({ top: rect.bottom + 4, left: rect.left });
                          setReindexTarget(doc._id);
                        }
                      }}
                    >
                      {reindexing === doc._id
                        ? <Loader2 size={14} className="kb-spin" />
                        : <ArrowRightLeft size={14} />}
                    </button>
                    {deleteConfirm === doc._id ? (
                      <button onClick={() => handleDelete(doc._id)} className="kb-confirm-yes">Xóa</button>
                    ) : (
                      <button onClick={() => setDeleteConfirm(doc._id)} className="kb-delete-btn"><Trash2 size={14} /></button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Dropdown chuyển ngăn — render ngoài table để tránh bị clip */}
      {reindexTarget && (() => {
        const doc = documents.find(d => d._id === reindexTarget);
        if (!doc) return null;
        return (
          <div
            className="kb-reindex-menu"
            style={{ position: 'fixed', top: dropdownPos.top, left: dropdownPos.left, zIndex: 9999 }}
          >
            <p>Chuyển sang ngăn:</p>
            {NAMESPACE_OPTIONS.filter(opt => !doc.pinecone_namespace?.includes(opt.id) && !doc.namespace_type?.includes(opt.id)).map(opt => (
              <button key={opt.id} onClick={() => handleReindex(doc._id, opt.id)}>
                <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: opt.color, marginRight: 6 }} />
                {opt.name}
              </button>
            ))}
          </div>
        );
      })()}
    </div>
  );
};

export default KnowledgeBase;
