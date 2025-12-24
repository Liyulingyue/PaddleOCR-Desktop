import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import OCRV5Page from './pages/OCRV5Page'
import HeaderBar from './components/HeaderBar'
import './styles/base.css'
import './styles/layout.css'
import './styles/header.css'
import './styles/upload.css'
import './styles/buttons.css'
import './styles/viewer.css'
import './styles/result.css'
import './pages/HomePage.css'

function App() {
  const handleSettingsClick = () => {
    alert('设置功能即将上线')
  }

  const handleAboutClick = () => {
    alert('PaddleOCR-Desktop v1.0.0\n基于PaddleOCR的桌面OCR应用\n\n技术栈：\n- 前端：React + TypeScript + Vite\n- 后端：Python + FastAPI\n- OCR引擎：PaddleOCR')
  }

  return (
    <Router>
      <HeaderBar
        onSettingsClick={handleSettingsClick}
        onAboutClick={handleAboutClick}
      />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/ocrv5" element={<OCRV5Page />} />
        <Route path="/ocrv4" element={<div>OCR V4 页面即将上线</div>} />
      </Routes>
    </Router>
  )
}

export default App
