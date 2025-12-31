import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import OCRV5Page from './pages/OCRV5Page'
import PPStructureV3Page from './pages/PPStructureV3Page'
import HeaderBar from './components/HeaderBar'
import { TauriCloseHandler } from './components/TauriCloseHandler'
import { BackendLogPanel } from './components/BackendLogPanel'
import { FrontendLogPanel } from './components/FrontendLogPanel'
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
      <FrontendLogPanel />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/ocrv5" element={<OCRV5Page />} />
        <Route path="/ppstructurev3" element={<PPStructureV3Page />} />
        <Route path="/ocrv4" element={<div>OCR V4 页面即将上线</div>} />
      </Routes>
    </Router>
  )
}

export default App
