import { Link } from 'react-router-dom'
import { useState } from 'react'

interface HeaderBarProps {
  title?: string
}

function HeaderBar({
  title = 'PaddleOCR Desktop'
}: HeaderBarProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen)
  }

  const closeSidebar = () => {
    setIsSidebarOpen(false)
  }

  return (
    <>
      <header className="header-bar">
        <div className="header-content">
          <div className="header-left">
            <button
              className="menu-btn"
              onClick={toggleSidebar}
              title="菜单"
            >
              ☰
            </button>
            <Link to="/" className="home-link" onClick={closeSidebar}>
              <h1 className="app-title">{title}</h1>
            </Link>
          </div>
        </div>
      </header>

      {/* Sidebar */}
      <div className={`sidebar ${isSidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-overlay" onClick={closeSidebar}></div>
        <div className="sidebar-content">
          <div className="sidebar-header">
            <h2>导航菜单</h2>
            <button className="sidebar-close" onClick={closeSidebar}>✕</button>
          </div>
          <nav className="sidebar-nav">
            <Link to="/" className="sidebar-link" onClick={closeSidebar}>
              🏠 首页
            </Link>
            <Link to="/ocrv5" className="sidebar-link" onClick={closeSidebar}>
              🤖 OCR识别 (V5)
            </Link>
            <Link to="/ppstructurev3" className="sidebar-link" onClick={closeSidebar}>
              📄 PP-Structure V3 布局检测
            </Link>
            {/* <Link to="/ocrv4" className="sidebar-link" onClick={closeSidebar}>
              📷 OCR识别 (V4)
            </Link> */}
          </nav>
        </div>
      </div>
    </>
  )
}

export default HeaderBar