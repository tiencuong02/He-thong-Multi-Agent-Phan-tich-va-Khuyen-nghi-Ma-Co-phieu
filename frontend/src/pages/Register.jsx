import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Lock, ShieldCheck, Loader2, CheckCircle, Eye, EyeOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import AuthBackground from '../components/AuthBackground';

const PASSWORD_RULES = [
  { test: p => p.length >= 8,         label: 'At least 8 characters' },
  { test: p => /[A-Z]/.test(p),       label: 'At least one uppercase letter' },
  { test: p => /[0-9]/.test(p),       label: 'At least one digit' },
];

const Register = () => {
  const [form, setForm] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    security_phrase: '',
  });
  const [showPwd, setShowPwd]         = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError]   = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = e =>
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (form.security_phrase.trim().length < 10) {
      setError('Security phrase must be at least 10 characters');
      return;
    }

    setLoading(true);
    try {
      await register(form.username, form.password, form.security_phrase);
      setSuccess(true);
    } catch (err) {
      const msg = err.response?.data?.detail;
      if (msg === 'Username already exists') {
        setError('This username is already taken. Please choose another.');
      } else if (msg?.includes('uppercase')) {
        setError('Password must contain at least one uppercase letter.');
      } else if (msg?.includes('digit')) {
        setError('Password must contain at least one digit.');
      } else if (msg?.includes('8 characters')) {
        setError('Password must be at least 8 characters.');
      } else if (err.code === 'ERR_NETWORK') {
        setError('Cannot connect to server. Please try again.');
      } else {
        setError(msg || 'Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const pwdStrength = PASSWORD_RULES.filter(r => r.test(form.password));

  return (
    <div className="lp-bg">
      <AuthBackground />

      <motion.div
        className="lp-card"
        style={{ maxWidth: 420 }}
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        <AnimatePresence mode="wait">
          {success ? (
            <motion.div
              key="success"
              className="lp-success"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <CheckCircle size={56} className="lp-success-icon" />
              <h2 className="lp-heading" style={{ fontSize: '1.4rem', marginBottom: '0.25rem' }}>
                Account Created!
              </h2>
              <p className="lp-success-msg">
                Your account has been created successfully. You can now log in.
              </p>
              <button className="lp-submit" onClick={() => navigate('/login')}>
                Go to Login
              </button>
            </motion.div>
          ) : (
            <motion.div key="form" initial={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <h1 className="lp-heading">Register</h1>

              {error && (
                <motion.div
                  className="lp-error"
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  {error}
                </motion.div>
              )}

              <form onSubmit={handleSubmit} className="lp-form">
                {/* Username */}
                <div className="lp-field">
                  <input
                    type="text"
                    name="username"
                    value={form.username}
                    onChange={handleChange}
                    className="lp-input"
                    placeholder="Username"
                    required
                    autoFocus
                    autoComplete="username"
                  />
                  <User className="lp-icon" size={18} />
                </div>

                {/* Password */}
                <div className="lp-field">
                  <input
                    type={showPwd ? 'text' : 'password'}
                    name="password"
                    value={form.password}
                    onChange={handleChange}
                    className="lp-input"
                    placeholder="Password"
                    required
                    autoComplete="new-password"
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

                {/* Password strength hints */}
                {form.password && (
                  <div className="lp-pwd-hints">
                    {PASSWORD_RULES.map(r => (
                      <span
                        key={r.label}
                        className={`lp-pwd-hint ${r.test(form.password) ? 'ok' : ''}`}
                      >
                        {r.test(form.password) ? '✓' : '·'} {r.label}
                      </span>
                    ))}
                  </div>
                )}

                {/* Confirm Password */}
                <div className="lp-field">
                  <input
                    type={showConfirm ? 'text' : 'password'}
                    name="confirmPassword"
                    value={form.confirmPassword}
                    onChange={handleChange}
                    className="lp-input"
                    placeholder="Confirm Password"
                    required
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="lp-eye-btn"
                    onClick={() => setShowConfirm(v => !v)}
                    tabIndex={-1}
                  >
                    {showConfirm ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>

                {/* Security Phrase */}
                <div className="lp-field">
                  <input
                    type="text"
                    name="security_phrase"
                    value={form.security_phrase}
                    onChange={handleChange}
                    className="lp-input"
                    placeholder="Security phrase (for password recovery)"
                    required
                    autoComplete="off"
                  />
                  <ShieldCheck className="lp-icon" size={18} />
                </div>
                <p className="lp-hint">
                  Enter a memorable sentence only you know — e.g. <em>"Con mèo của tôi tên là Bông"</em>. You'll need this to reset your password.
                </p>

                <button type="submit" disabled={loading} className="lp-submit">
                  {loading ? <Loader2 className="animate-spin" size={20} /> : 'Create Account'}
                </button>
              </form>

              <p className="lp-footer-text">
                Already have an account?{' '}
                <Link to="/login" className="lp-link">Login</Link>
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

export default Register;
