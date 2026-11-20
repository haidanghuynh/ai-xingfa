import React from 'react'
import { createRoot } from 'react-dom/client'
import App from '@/App'
import { ToastProvider } from '@/components/ui/overlays'
import '@/index.css'

const container = document.getElementById('root')
if (!container) throw new Error('Không tìm thấy #root')

createRoot(container).render(
  <React.StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </React.StrictMode>,
)
