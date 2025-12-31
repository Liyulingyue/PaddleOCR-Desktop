import { useState } from 'react'
import ControlBar from '../components/ControlBar'
import Viewer from '../components/Viewer'
import ResultPanel from '../components/ResultPanel'

function PPStructureV3Page() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<any>(null)
  const [drawnImage, setDrawnImage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState({
    confThreshold: 0.5
  })
  const [message, setMessage] = useState<string | null>(null)
  const [showApiModal, setShowApiModal] = useState(false)

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setResult(null)
    setDrawnImage(null)
  }

  const handleConfigChange = (newConfig: { confThreshold: number }) => {
    setConfig(newConfig)
  }

  const handleClear = () => {
    setFile(null)
    setResult(null)
    setDrawnImage(null)
    setError(null)
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('conf_threshold', config.confThreshold.toString())

    try {
      // Fetch layout detection result
      const response = await fetch('http://localhost:8000/api/ppstructure', {
        method: 'POST',
        body: formData,
      })
      const data = await response.json()
      if (response.ok) {
        setResult(data.result)
      } else {
        setError(data.error || '上传失败')
      }

      // Fetch drawn image
      const drawFormData = new FormData()
      drawFormData.append('file', file)
      drawFormData.append('layout_result', JSON.stringify(data))
      const drawResponse = await fetch('http://localhost:8000/api/ppstructure/draw', {
        method: 'POST',
        body: drawFormData,
      })
      if (drawResponse.ok) {
        const blob = await drawResponse.blob()
        const imageUrl = URL.createObjectURL(blob)
        setDrawnImage(imageUrl)
      } else {
        console.error('Failed to fetch drawn image')
      }
    } catch (err) {
      setError('网络错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="layout">
      {message && (
        <div className="global-message-banner">
          {message}
        </div>
      )}

      <ControlBar
        onFileSelect={handleFileSelect}
        file={file}
        loading={loading}
        error={error}
        onUpload={handleUpload}
        onClear={handleClear}
        config={config}
        onConfigChange={handleConfigChange}
        onShowApiModal={() => setShowApiModal(true)}
        pageType="ppstructure"
      />
      <Viewer file={file} />
      <ResultPanel result={result} imageFile={file} drawnImage={drawnImage} onMessage={setMessage} resultType="layout" />

      {showApiModal && (
        <div className="api-modal-overlay" onClick={() => setShowApiModal(false)}>
          <div className="api-modal" onClick={(e) => e.stopPropagation()}>
            <div className="api-modal-header">
              <h3>API 文档</h3>
              <button className="close-btn" onClick={() => setShowApiModal(false)}>×</button>
            </div>
            <div className="api-modal-content">
              <div className="api-section">
                <h4>🔗 接口地址</h4>
                <code className="api-url">http://localhost:8000</code>
              </div>

              <div className="api-section">
                <h4>📝 PP-Structure V3 布局检测接口</h4>
                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ppstructure</code>
                </div>
                <div className="api-params">
                  <h5>参数：</h5>
                  <ul>
                    <li><code>file</code>: 上传的图像文件</li>
                    <li><code>conf_threshold</code>: 置信度阈值 (0.0-1.0，默认: 0.5)</li>
                  </ul>
                </div>
              </div>

              <div className="api-section">
                <h4>🎨 可视化接口</h4>
                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ppstructure/draw</code>
                </div>
                <div className="api-params">
                  <h5>参数：</h5>
                  <ul>
                    <li><code>file</code>: 原始图像文件</li>
                    <li><code>layout_result</code>: 布局检测结果的JSON字符串</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PPStructureV3Page