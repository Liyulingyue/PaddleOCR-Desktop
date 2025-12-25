import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import OCRV5Page from './pages/OCRV5Page'
import HeaderBar from './components/HeaderBar'
import { TauriCloseHandler } from './components/TauriCloseHandler'
import { BackendLogPanel } from './components/BackendLogPanel'
import './styles/base.css'
import './styles/layout.css'
import './styles/header.css'
import './styles/upload.css'
import './styles/buttons.css'
import './styles/viewer.css'
import './styles/result.css'
import './pages/HomePage.css'

function App() {
  return (
    <Router>
      <HeaderBar />
      <TauriCloseHandler />
      <BackendLogPanel />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/ocrv5" element={<OCRV5Page />} />
        <Route path="/ocrv4" element={<div>OCR V4 页面即将上线</div>} />
      </Routes>
    </Router>
  )
}

export default App
