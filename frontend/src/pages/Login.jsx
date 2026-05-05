import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { User, Lock, ShieldCheck, Loader2, Eye, EyeOff, CheckCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import AuthBackground from '../components/AuthBackground';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const PASSWORD_RULES = [
  { test: p => p.length >= 8,   label: 'At least 8 characters' },
  { test: p => /[A-Z]/.test(p), label: 'At least one uppercase letter' },
  { test: p => /[0-9]/.test(p), label: 'At least one digit' },
];

/* ── Forgot-password modal (3 steps) ───────────────── */
const ForgotModal = ({ onClose }) => {
  const [step, setStep]               = useState(1); // 1 = verify, 2 = reset, 3 = done
  const [username, setUsername]       = useState('');
  const [phrase, setPhrase]           = useState('');
  const [resetToken, setResetToken]   = useState('');
  const [newPwd, setNewPwd]           = useState('');
  const [confirmPwd, setConfirmPwd]   = useState('');
  const [showPwd, setShowPwd]         = useState(false);
  const [error, setError]             = useState('');
  const [loading, setLoading]         = useState(false);

  const handleVerify = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/auth/forgot-password/verify`, {
        username: username.trim(),
        security_phrase: phrase,
      });
      setResetToken(res.data.reset_token);
      setStep(2);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.includes('no security phrase')) {
        setError('This account has no security phrase. Please contact administrator.');
      } else if (detail?.includes('not found')) {
        setError('Username not found.');
      } else if (err.response?.status === 401) {
        setError('Incorrect security phrase. Please try again.');
      } else if (err.code === 'ERR_NETWORK') {
        setError('Cannot connect to server.');
      } else {
        setError(detail || 'Verification failed.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    setError('');
    if (newPwd !== confirmPwd) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API_URL}/auth/forgot-password/reset`, {
        reset_token: resetToken,
        new_password: newPwd,
      });
      setStep(3);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.includes('expired')) {
        setError('Reset link expired. Please start over.');
      } else if (detail?.includes('uppercase')) {
        setError('Password must contain at least one uppercase letter.');
      } else if (detail?.includes('digit')) {
        setError('Password must contain at least one digit.');
      } else if (detail?.includes('8 characters')) {
        setError('Password must be at least 8 characters.');
      } else {
        setError(detail || 'Reset failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="lp-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={step !== 3 ? onClose : undefined}
    >
      <motion.div
        className="lp-modal"
        style={{ maxWidth: 380 }}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        onClick={e => e.stopPropagation()}
      >
        <AnimatePresence mode="wait">

          {/* ── Step 1: Verify identity ── */}
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              <div className="lp-modal-icon">🔐</div>
              <h3 className="lp-modal-title">Reset Password</h3>
              <p className="lp-modal-body">
                Enter your username and the security phrase you set when registering.
              </p>

              {error && <div className="lp-error" style={{ marginBottom: '1rem' }}>{error}</div>}

              <form onSubmit={handleVerify} className="lp-form" style={{ gap: '0.75rem' }}>
                <div className="lp-field">
                  <input
                    type="text"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    className="lp-input"
                    placeholder="Username"
                    required
                    autoFocus
                  />
                  <User className="lp-icon" size={17} />
                </div>
                <div className="lp-field">
                  <input
                    type="text"
                    value={phrase}
                    onChange={e => setPhrase(e.target.value)}
                    className="lp-input"
                    placeholder="Your security phrase"
                    required
                    autoComplete="off"
                  />
                  <ShieldCheck className="lp-icon" size={17} />
                </div>
                <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.25rem' }}>
                  <button
                    type="button"
                    className="lp-modal-btn"
                    style={{ flex: 1, background: 'rgba(255,255,255,0.15)', color: 'white' }}
                    onClick={onClose}
                  >
                    Cancel
                  </button>
                  <button type="submit" className="lp-modal-btn" style={{ flex: 2 }} disabled={loading}>
                    {loading ? <Loader2 size={16} className="animate-spin" style={{ display: 'inline' }} /> : 'Verify →'}
                  </button>
                </div>
              </form>
            </motion.div>
          )}

          {/* ── Step 2: Set new password ── */}
          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              <div className="lp-modal-icon">🔑</div>
              <h3 className="lp-modal-title">New Password</h3>
              <p className="lp-modal-body">Identity verified. Enter your new password.</p>

              {error && <div className="lp-error" style={{ marginBottom: '1rem' }}>{error}</div>}

              <form onSubmit={handleReset} className="lp-form" style={{ gap: '0.75rem' }}>
                <div className="lp-field">
                  <input
                    type={showPwd ? 'text' : 'password'}
                    value={newPwd}
                    onChange={e => setNewPwd(e.target.value)}
                    className="lp-input"
                    placeholder="New password"
                    required
                    autoFocus
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="lp-eye-btn"
                    onClick={() => setShowPwd(v => !v)}
                    tabIndex={-1}
                  >
                    {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>

                {newPwd && (
                  <div className="lp-pwd-hints">
                    {PASSWORD_RULES.map(r => (
                      <span key={r.label} className={`lp-pwd-hint ${r.test(newPwd) ? 'ok' : ''}`}>
                        {r.test(newPwd) ? '✓' : '·'} {r.label}
                      </span>
                    ))}
                  </div>
                )}

                <div className="lp-field">
                  <input
                    type={showPwd ? 'text' : 'password'}
                    value={confirmPwd}
                    onChange={e => setConfirmPwd(e.target.value)}
                    className="lp-input"
                    placeholder="Confirm new password"
                    required
                    autoComplete="new-password"
                  />
                  <Lock className="lp-icon" size={17} />
                </div>

                <button
                  type="submit"
                  className="lp-modal-btn"
                  style={{ width: '100%', marginTop: '0.25rem' }}
                  disabled={loading}
                >
                  {loading
                    ? <Loader2 size={16} className="animate-spin" style={{ display: 'inline' }} />
                    : 'Reset Password'}
                </button>
              </form>
            </motion.div>
          )}

          {/* ── Step 3: Success ── */}
          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{ textAlign: 'center' }}
            >
              <CheckCircle size={52} style={{ color: '#4ade80', marginBottom: '1rem', filter: 'drop-shadow(0 0 12px rgba(74,222,128,0.5))' }} />
              <h3 className="lp-modal-title">Password Reset!</h3>
              <p className="lp-modal-body">
                Your password has been updated. You can now log in with your new password.
              </p>
              <button className="lp-modal-btn" onClick={onClose}>
                Back to Login
              </button>
            </motion.div>
          )}

        </AnimatePresence>
      </motion.div>
    </motion.div>
  );
};

/* ── Login page ───────────────────────────────────── */
const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd]   = useState(false);
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [showForgot, setShowForgot] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      if (err.code === 'ERR_NETWORK') {
        setError('Cannot connect to server. Please ensure the backend is running.');
      } else {
        setError('Invalid username or password.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="lp-bg">
      <AuthBackground />

      <AnimatePresence>
        {showForgot && <ForgotModal onClose={() => setShowForgot(false)} />}
      </AnimatePresence>

      <motion.div
        className="lp-card"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        <h1 className="lp-heading">Login</h1>

        {error && (
          <motion.div className="lp-error" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}>
            {error}
          </motion.div>
        )}

        <form onSubmit={handleSubmit} className="lp-form">
          <div className="lp-field">
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="lp-input"
              placeholder="Username"
              required
              autoFocus
              autoComplete="username"
            />
            <User className="lp-icon" size={18} />
          </div>

          <div className="lp-field">
            <input
              type={showPwd ? 'text' : 'password'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="lp-input"
              placeholder="Password"
              required
              autoComplete="current-password"
            />
            <button
              type="button"
              className="lp-eye-btn"
              onClick={() => setShowPwd(v => !v)}
              tabIndex={-1}
            >
              {showPwd ? <EyeOff size={17} /> : <Eye size={17} />}
            </button>
          </div>

          <div className="lp-row">
            <label className="lp-check">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={e => setRememberMe(e.target.checked)}
                className="lp-checkbox"
              />
              <span>Remember me</span>
            </label>
            <button type="button" className="lp-link-btn" onClick={() => setShowForgot(true)}>
              Forgot password?
            </button>
          </div>

          <button type="submit" disabled={loading} className="lp-submit">
            {loading ? <Loader2 className="animate-spin" size={20} /> : 'Login'}
          </button>
        </form>

        <p className="lp-footer-text">
          Don't have an account?{' '}
          <Link to="/register" className="lp-link">Register</Link>
        </p>
      </motion.div>
    </div>
  );
};

export default Login;
