import React from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import App from './App'
import './index.css'

// Global axios interceptor: tự động gắn auth token + bypass ngrok interstitial
axios.interceptors.request.use((config) => {
  config.headers['ngrok-skip-browser-warning'] = 'true'
  const token = sessionStorage.getItem('token')
  if (token && !config.headers['Authorization']) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
