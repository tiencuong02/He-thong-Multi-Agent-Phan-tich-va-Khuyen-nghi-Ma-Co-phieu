import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import {
  Upload, FileText, Trash2, RefreshCw, CheckCircle2,
  AlertCircle, BookOpen, X, ChevronDown
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const DOC_TYPE_OPTIONS = [
  'Báo cáo tài chính',
  'Báo cáo thường niên',
  'Báo cáo phân tích',
];

const PERIOD_OPTIONS = ['Q1', 'Q2', 'Q3', 'Q4', 'Cả năm'];

const KnowledgeBase = () => {
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  // ─── State ────────────────────────────────────────────────────────────
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null); // {type: 'success'|'error', message}
  const [dragActive, setDragActive] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const fileInputRef = useRef(null);

  // Form fields
  const [selectedFile, setSelectedFile] = useState(null);
  const [ticker, setTicker] = useState('');
  const [docType, setDocType] = useState(DOC_TYPE_OPTIONS[0]);
  const [period, setPeriod] = useState(PERIOD_OPTIONS[0]);
  const [year, setYear] = useState('2024');

  // ─── Fetch Documents ──────────────────────────────────────────────────
  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/rag/documents/`, { headers });
      setDocuments(res.data || []);
    } catch (err) {
      console.error('Failed to fetch documents', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  // ─── Upload Handler ───────────────────────────────────────────────────
  const handleUpload = async () => {
    if (!selectedFile || !ticker.trim()) {
      setUploadResult({ type: 'error', message: 'Vui lòng chọn file PDF và nhập mã cổ phiếu.' });
      return;
    }

    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('ticker', ticker.trim().toUpperCase());
    formData.append('doc_type', docType);
    formData.append('period', period);
    formData.append('year', year);

    try {
      const res = await axios.post(`${API_BASE_URL}/rag/upload/`, formData, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
        timeout: 120000, // 2 min timeout for large files
      });

      setUploadResult({
        type: 'success',
        message: `✅ ${res.data.message} — ${res.data.chunks_processed} chunks đã được xử lý.`
      });

      // Reset form
      setSelectedFile(null);
      setTicker('');
      if (fileInputRef.current) fileInputRef.current.value = '';

      // Refresh document list
      fetchDocuments();
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setUploadResult({ type: 'error', message: `❌ Upload thất bại: ${detail}` });
    } finally {
      setUploading(false);
    }
  };

  // ─── Delete Handler ───────────────────────────────────────────────────
  const handleDelete = async (docId) => {
    try {
      await axios.delete(`${API_BASE_URL}/rag/documents/${docId}/`, { headers });
      setDocuments(prev => prev.filter(d => d._id !== docId));
      setDeleteConfirm(null);
    } catch (err) {
      console.error('Delete failed', err);
    }
  };

  // ─── Drag & Drop ──────────────────────────────────────────────────────
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.name.toLowerCase().endsWith('.pdf')) {
      setSelectedFile(file);
      setUploadResult(null);
    } else {
      setUploadResult({ type: 'error', message: 'Chỉ chấp nhận file PDF.' });
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadResult(null);
    }
  };

  // ─── Render ───────────────────────────────────────────────────────────
  return (
    <div className="fade-in">
      {/* ── Upload Section ── */}
      <div className="kb-upload-section">
        <div className="kb-section-header">
          <h3><Upload size={18} /> Upload Báo Cáo PDF</h3>
        </div>

        {/* Drop Zone */}
        <div
          className={`kb-dropzone ${dragActive ? 'active' : ''} ${selectedFile ? 'has-file' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
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
              <span className="kb-filesize">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </span>
              <button
                className="kb-remove-file"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
              >
                <X size={16} />
              </button>
            </div>
          ) : (
            <div className="kb-drop-placeholder">
              <Upload size={40} strokeWidth={1.5} />
              <p>Kéo thả file PDF vào đây</p>
              <span>hoặc click để chọn file</span>
            </div>
          )}
        </div>

        {/* Metadata Form */}
        <div className="kb-form-grid">
          <div className="kb-form-group">
            <label>Mã cổ phiếu *</label>
            <input
              type="text"
              placeholder="VD: FPT, HPG, VNM"
              value={ticker}
              onChange={e => setTicker(e.target.value.toUpperCase())}
              className="kb-input"
              maxLength={10}
            />
          </div>

          <div className="kb-form-group">
            <label>Loại tài liệu</label>
            <div className="kb-select-wrapper">
              <select value={docType} onChange={e => setDocType(e.target.value)} className="kb-input">
                {DOC_TYPE_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
              </select>
              <ChevronDown size={14} className="kb-select-icon" />
            </div>
          </div>

          <div className="kb-form-group">
            <label>Kỳ báo cáo</label>
            <div className="kb-select-wrapper">
              <select value={period} onChange={e => setPeriod(e.target.value)} className="kb-input">
                {PERIOD_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
              </select>
              <ChevronDown size={14} className="kb-select-icon" />
            </div>
          </div>

          <div className="kb-form-group">
            <label>Năm</label>
            <input
              type="text"
              placeholder="VD: 2024"
              value={year}
              onChange={e => setYear(e.target.value)}
              className="kb-input"
              maxLength={4}
            />
          </div>
        </div>

        {/* Upload Button */}
        <button
          className="kb-upload-btn"
          onClick={handleUpload}
          disabled={uploading || !selectedFile || !ticker.trim()}
        >
          {uploading ? (
            <>
              <RefreshCw size={16} className="kb-spin" />
              Đang xử lý PDF...
            </>
          ) : (
            <>
              <Upload size={16} />
              Upload & Xử lý
            </>
          )}
        </button>

        {/* Result Message */}
        {uploadResult && (
          <div className={`kb-alert ${uploadResult.type}`}>
            {uploadResult.type === 'success'
              ? <CheckCircle2 size={16} />
              : <AlertCircle size={16} />
            }
            <span>{uploadResult.message}</span>
          </div>
        )}
      </div>

      {/* ── Documents List ── */}
      <div className="kb-docs-section">
        <div className="kb-section-header">
          <h3><BookOpen size={18} /> Tài liệu đã nạp ({documents.length})</h3>
          <button onClick={fetchDocuments} className="kb-refresh-btn" title="Refresh">
            <RefreshCw size={15} />
          </button>
        </div>

        {loading ? (
          <div className="kb-loading">Đang tải danh sách...</div>
        ) : documents.length === 0 ? (
          <div className="kb-empty">
            <FileText size={48} strokeWidth={1} />
            <p>Chưa có tài liệu nào trong Knowledge Base</p>
            <span>Upload file PDF báo cáo tài chính để bắt đầu</span>
          </div>
        ) : (
          <div className="kb-table-wrapper">
            <table className="kb-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Tên file</th>
                  <th>Mã CK</th>
                  <th>Loại</th>
                  <th>Kỳ</th>
                  <th>Năm</th>
                  <th>Chunks</th>
                  <th>Ngày upload</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc, idx) => (
                  <tr key={doc._id}>
                    <td className="kb-td-num">{idx + 1}</td>
                    <td className="kb-td-filename">
                      <FileText size={14} />
                      <span>{doc.filename}</span>
                    </td>
                    <td><span className="kb-ticker-badge">{doc.ticker}</span></td>
                    <td className="kb-td-type">{doc.doc_type}</td>
                    <td>{doc.period}</td>
                    <td>{doc.year}</td>
                    <td className="kb-td-chunks">{doc.chunks_count}</td>
                    <td className="kb-td-date">
                      {doc.uploaded_at
                        ? new Date(doc.uploaded_at).toLocaleDateString('vi-VN')
                        : '—'}
                    </td>
                    <td>
                      {deleteConfirm === doc._id ? (
                        <div className="kb-delete-confirm">
                          <button onClick={() => handleDelete(doc._id)} className="kb-confirm-yes">Xóa</button>
                          <button onClick={() => setDeleteConfirm(null)} className="kb-confirm-no">Hủy</button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirm(doc._id)}
                          className="kb-delete-btn"
                          title="Xóa tài liệu"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default KnowledgeBase;
