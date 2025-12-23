import OCRPage from './pages/OCRPage'
import HeaderBar from './components/HeaderBar'
import './styles/base.css'
import './styles/layout.css'
import './styles/header.css'
import './styles/upload.css'
import './styles/buttons.css'
import './styles/viewer.css'
import './styles/result.css'

function App() {
  const handleSettingsClick = () => {
    alert('设置功能即将上线')
  }

  const handleAboutClick = () => {
    alert('PaddleOCR-Desktop v1.0.0\n基于PaddleOCR的桌面OCR应用\n\n技术栈：\n- 前端：React + TypeScript + Vite\n- 后端：Python + FastAPI\n- OCR引擎：PaddleOCR')
  }

  return (
    <>
      <HeaderBar
        onSettingsClick={handleSettingsClick}
        onAboutClick={handleAboutClick}
      />
      <OCRPage />
    </>
  )
}

export default App
