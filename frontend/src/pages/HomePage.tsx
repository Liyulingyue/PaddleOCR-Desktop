import { useNavigate } from 'react-router-dom'
import './HomePage.css'

function HomePage() {
  const navigate = useNavigate()

  return (
    <div className="home-page">
      <div className="hero-section">
        <div className="hero-inner">
          <div className="hero-content">
            <h1>PaddleOCR Desktop</h1>
            <p>基于PaddleOCR的强大桌面OCR应用</p>
            <div className="feature-buttons">
              <button className="primary-btn" onClick={() => navigate('/ocrv5')}>
                PP-OCR V5 文字识别
              </button>
              <button className="primary-btn" onClick={() => navigate('/ppstructurev3')}>
                PP-Structure V3 布局检测
              </button>
              <button className="primary-btn" onClick={() => navigate('/model-management')}>
                📦 模型管理
              </button>
            </div>
          </div>
          <div className="hero-visual" aria-hidden="true" style={{width: '320px', height: '280px', borderRadius: '12px', background: 'rgba(255,255,255,0.03)'}}></div>
        </div>
      </div>

      <div className="features-section">
        <h2>功能特性</h2>
        <div className="features-grid">
          <div className="feature-card">
            <h3>多模型支持</h3>
            <p>支持PaddleOCR V5和PP-Structure V3，提供高精度识别和布局检测</p>
          </div>
          <div className="feature-card">
            <h3>布局检测</h3>
            <p>PP-Structure V3模型支持文档布局分析，识别表格、公式、图像等元素</p>
          </div>
          <div className="feature-card">
            <h3>图像绘制</h3>
            <p>自动绘制识别框和文本，方便结果查看</p>
          </div>
          <div className="feature-card">
            <h3>多种格式</h3>
            <p>支持图片和PDF文件，批量处理</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HomePage