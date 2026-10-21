import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Buffer } from 'buffer'
import App from './App'
import './index.css'

;(globalThis as typeof globalThis & { Buffer: typeof Buffer }).Buffer = Buffer

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
