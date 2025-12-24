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
                开始OCR识别 (V5)
              </button>
              {/* <button className="secondary-btn" onClick={() => navigate('/ocrv4')}>
                OCR识别 (V4)
              </button> */}
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
            <p>支持PaddleOCR V4和V5模型，提供高精度识别</p>
          </div>
          <div className="feature-card">
            <h3>图像绘制</h3>
            <p>自动绘制识别框和文本，方便结果查看</p>
          </div>
          <div className="feature-card">
            <h3>多种格式</h3>
            <p>支持图片和PDF文件，批量处理</p>
          </div>
          <div className="feature-card">
            <h3>实时预览</h3>
            <p>上传后即时预览和识别结果</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HomePage