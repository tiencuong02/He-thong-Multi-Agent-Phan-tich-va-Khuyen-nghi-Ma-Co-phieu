import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Plus, Edit2, Trash2, Search, X, Check, Loader2, Quote as QuoteIcon, Filter, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const QuoteManagement = () => {
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setModalOpen] = useState(false);
  const [editingQuote, setEditingQuote] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    content: '',
    author: '',
    context: 'GENERAL'
  });

  const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchQuotes();
  }, []);

  const fetchQuotes = async () => {
    try {
      const response = await axios.get(`${API_URL}/quotes`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setQuotes(response.data);
    } catch (error) {
      console.error('Failed to fetch quotes', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (quote = null) => {
    if (quote) {
      setEditingQuote(quote);
      setFormData({
        content: quote.content,
        author: quote.author,
        context: quote.context
      });
    } else {
      setEditingQuote(null);
      setFormData({ content: '', author: '', context: 'GENERAL' });
    }
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      if (editingQuote) {
        await axios.put(`${API_URL}/quotes/${editingQuote.id}`, formData, {
          headers: { Authorization: `Bearer ${token}` }
        });
      } else {
        await axios.post(`${API_URL}/quotes`, formData, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }
      setModalOpen(false);
      fetchQuotes();
    } catch (error) {
      console.error('Failed to save quote', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this quote?')) return;
    try {
      await axios.delete(`${API_URL}/quotes/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchQuotes();
    } catch (error) {
      console.error('Failed to delete quote', error);
    }
  };

  const filteredQuotes = quotes.filter(q => 
    q.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
    q.author.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) return (
    <div className="loading-area">
      <Loader2 className="w-10 h-10 text-blue-500 animate-spin mx-auto" />
      <p className="text-gray-500 mt-4 font-medium">Loading database...</p>
    </div>
  );

  return (
    <div className="fade-in">
      <div className="admin-section">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between mb-8">
          <div className="relative w-full md:w-96 group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
            <input
              type="text"
              placeholder="Search quotes or authors..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white/[0.03] border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-sm focus:outline-none focus:border-blue-500/50 focus:bg-white/[0.05] transition-all"
            />
          </div>
          <div className="flex gap-3 w-full md:w-auto">
            <button className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-white/5 border border-white/10 hover:bg-white/10 px-4 py-3 rounded-2xl transition-all font-semibold text-gray-300">
               <Filter size={18} />
               <span>Filter</span>
            </button>
            <button 
              onClick={() => handleOpenModal()}
              className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-gradient-to-br from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 px-6 py-3 rounded-2xl transition-all font-bold shadow-lg shadow-blue-500/10"
            >
              <Plus size={20} />
              <span>New Quote</span>
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-gray-500 text-xs uppercase tracking-widest border-b border-white/5">
                <th className="pb-4 px-4 font-bold">Inspiration / Content</th>
                <th className="pb-4 px-4 font-bold">Author</th>
                <th className="pb-4 px-4 font-bold">Context</th>
                <th className="pb-4 px-4 font-bold text-right">Settings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredQuotes.map((quote) => (
                <tr key={quote.id} className="hover:bg-white/[0.01] transition-colors group">
                  <td className="py-5 px-4">
                      <div className="flex items-start gap-3">
                          <div className="mt-1 opacity-20 group-hover:opacity-100 transition-opacity">
                              <QuoteIcon size={14} className="text-blue-400" />
                          </div>
                          <p className="text-gray-300 text-sm leading-relaxed max-w-xl line-clamp-2">{quote.content}</p>
                      </div>
                  </td>
                  <td className="py-5 px-4 font-bold text-white text-sm">{quote.author}</td>
                  <td className="py-5 px-4">
                    <span className={`px-3 py-1 rounded-lg text-[10px] font-black tracking-widest ${
                      quote.context === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      quote.context === 'SELL' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                      'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                    }`}>
                      {quote.context}
                    </span>
                  </td>
                  <td className="py-5 px-4">
                    <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button 
                        onClick={() => handleOpenModal(quote)}
                        className="p-2 hover:bg-blue-500/10 rounded-xl text-gray-400 hover:text-blue-400 transition-all"
                      >
                        <Edit2 size={16} />
                      </button>
                      <button 
                        onClick={() => handleDelete(quote.id)}
                        className="p-2 hover:bg-rose-500/10 rounded-xl text-gray-400 hover:text-rose-400 transition-all"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredQuotes.length === 0 && (
              <div className="py-20 text-center">
                  <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4 border border-dashed border-white/10">
                    <Search size={24} className="text-gray-600" />
                  </div>
                  <h4 className="text-gray-400 font-bold">No quotes found</h4>
                  <p className="text-gray-600 text-sm">Try adjusting your search criteria</p>
              </div>
          )}
        </div>
      </div>

      {/* Modal */}
      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setModalOpen(false)}
              className="absolute inset-0 bg-black/80 backdrop-blur-md"
            />
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="relative w-full max-w-xl bg-[#0f172a] border border-white/10 rounded-[2rem] p-8 shadow-2xl"
            >
              <div className="flex justify-between items-center mb-8">
                <div>
                    <h3 className="text-2xl font-black text-white">
                        {editingQuote ? 'Update entry' : 'Create entry'}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">Fill in the details for the quote database</p>
                </div>
                <button onClick={() => setModalOpen(false)} className="p-2 hover:bg-white/5 rounded-full transition-colors">
                  <X size={24} className="text-gray-500" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <label className="text-xs font-bold text-blue-400 uppercase tracking-widest ml-1">Content</label>
                  <textarea
                    required
                    rows={4}
                    value={formData.content}
                    onChange={(e) => setFormData({...formData, content: e.target.value})}
                    className="w-full bg-white/[0.03] border border-white/10 rounded-2xl p-4 text-sm focus:outline-none focus:border-blue-500/50 focus:bg-white/[0.05]"
                    placeholder="Enter the quote text..."
                  />
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-blue-400 uppercase tracking-widest ml-1">Author</label>
                    <input
                      type="text"
                      required
                      value={formData.author}
                      onChange={(e) => setFormData({...formData, author: e.target.value})}
                      className="w-full bg-white/[0.03] border border-white/10 rounded-2xl p-4 text-sm focus:outline-none focus:border-blue-500/50 focus:bg-white/[0.05]"
                      placeholder="e.g. Warren Buffett"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-blue-400 uppercase tracking-widest ml-1">Context</label>
                    <div className="relative">
                        <select
                          value={formData.context}
                          onChange={(e) => setFormData({...formData, context: e.target.value})}
                          className="w-full bg-white/[0.03] border border-white/10 rounded-2xl p-4 text-sm appearance-none focus:outline-none focus:border-blue-500/50 focus:bg-white/[0.05]"
                        >
                          <option value="GENERAL">📊 General</option>
                          <option value="BUY">📈 Buy Signal</option>
                          <option value="SELL">📉 Sell Signal</option>
                        </select>
                        <ChevronDown size={14} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
                    </div>
                  </div>
                </div>

                <div className="pt-6 flex gap-4">
                  <button
                    type="button"
                    onClick={() => setModalOpen(false)}
                    className="flex-1 px-6 py-4 bg-white/5 border border-white/10 rounded-2xl hover:bg-white/10 transition-all font-bold text-gray-300"
                  >
                    Discard
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-br from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 px-6 py-4 rounded-2xl transition-all font-bold text-white shadow-xl shadow-blue-500/20"
                  >
                    {isSubmitting ? <Loader2 size={20} className="animate-spin" /> : editingQuote ? 'Apply changes' : 'Save entries'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default QuoteManagement;
