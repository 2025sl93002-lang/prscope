// App entry. SPDX-License-Identifier: MIT
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ToastProvider } from './components/Toast'
import { ActiveAnalysisProvider } from './active'
import { applyTheme } from './hooks'
import './styles.css'

applyTheme((localStorage.getItem('prscope-theme') as 'system' | 'light' | 'dark') || 'system')

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <ActiveAnalysisProvider>
          <App />
        </ActiveAnalysisProvider>
      </ToastProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
