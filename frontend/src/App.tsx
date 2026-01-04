import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import OCRV5Page from './pages/OCRV5Page'
import PPStructureV3Page from './pages/PPStructureV3Page'
import ModelManagementPage from './pages/ModelManagementPage'
import HeaderBar from './components/HeaderBar'
import { TauriCloseHandler } from './components/TauriCloseHandler'
import { BackendLogPanel } from './components/BackendLogPanel'
import { FrontendLogPanel } from './components/FrontendLogPanel'
import LoadingPage from './components/LoadingPage'
import './styles/base.css'
import './styles/layout.css'
import './styles/header.css'
import './styles/upload.css'
import './styles/buttons.css'
import './styles/viewer.css'
import './styles/result.css'
import './styles/loading.css'
import './pages/HomePage.css'

// 检查是否在 Tauri 环境中
const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined

function App() {
  const [backendReady, setBackendReady] = useState(!isTauri) // 非Tauri环境直接认为ready
  const [showLoading, setShowLoading] = useState(isTauri) // Tauri环境才显示加载页面

  const handleBackendReady = () => {
    setBackendReady(true)
    setShowLoading(false)
  }

  // 如果后端已准备好，隐藏加载页面
  useEffect(() => {
    if (backendReady) {
      setShowLoading(false)
    }
  }, [backendReady])

  return (
    <Router>
      {showLoading ? (
        <LoadingPage onBackendReady={handleBackendReady} maxWaitTime={120000} />
      ) : (
        <>
          <HeaderBar />
          {isTauri && <TauriCloseHandler />}
          {isTauri && <BackendLogPanel />}
          <FrontendLogPanel />
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/ocrv5" element={<OCRV5Page />} />
            <Route path="/ppstructurev3" element={<PPStructureV3Page />} />
            <Route path="/model-management" element={<ModelManagementPage />} />
          </Routes>
        </>
      )}
    </Router>
  )
}

export default App
