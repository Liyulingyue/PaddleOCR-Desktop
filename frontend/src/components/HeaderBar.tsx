interface HeaderBarProps {
  title?: string
  onSettingsClick?: () => void
  onAboutClick?: () => void
}

function HeaderBar({
  title = 'PaddleOCR-Desktop',
  onSettingsClick,
  onAboutClick
}: HeaderBarProps) {
  const handleSettingsClick = () => {
    if (onSettingsClick) {
      onSettingsClick()
    } else {
      alert('设置功能即将上线')
    }
  }

  const handleAboutClick = () => {
    if (onAboutClick) {
      onAboutClick()
    } else {
      alert('PaddleOCR-Desktop v1.0.0\n基于PaddleOCR的桌面OCR应用')
    }
  }

  return (
    <header className="header-bar">
      <div className="header-content">
        <h1 className="app-title">{title}</h1>
        <div className="header-actions">
          <button
            className="header-btn settings-btn"
            onClick={handleSettingsClick}
            title="设置"
          >
            ⚙️
          </button>
          <button
            className="header-btn about-btn"
            onClick={handleAboutClick}
            title="关于"
          >
            ℹ️
          </button>
        </div>
      </div>
    </header>
  )
}

export default HeaderBar