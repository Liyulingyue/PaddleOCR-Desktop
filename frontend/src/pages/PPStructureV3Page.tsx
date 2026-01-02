import { useState, useEffect } from 'react'
import ControlBar from '../components/ControlBar'
import Viewer from '../components/Viewer'
import ResultPanel from '../components/ResultPanel'
import { getCachedApiBaseUrl } from '../utils/api'

function PPStructureV3Page() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<any>(null)
  const [drawnImage, setDrawnImage] = useState<string | null>(null)
  const [markdownContent, setMarkdownContent] = useState<string | null>(null)
  const [markdownImageData, setMarkdownImageData] = useState<string | null>(null)
  const [markdownImages, setMarkdownImages] = useState<{ [key: string]: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState({
    confThreshold: 0.5,
    ocrDetThresh: 0.3,
    unclipRatio: 1.1
  })
  const [message, setMessage] = useState<string | null>(null)
  const [showApiModal, setShowApiModal] = useState(false)
  const [apiBaseUrl, setApiBaseUrl] = useState<string>('')

  // 获取API基础URL
  useEffect(() => {
    const fetchApiUrl = async () => {
      try {
        const url = await getCachedApiBaseUrl()
        setApiBaseUrl(url)
      } catch (error) {
        console.error('Failed to get API URL:', error)
      }
    }
    fetchApiUrl()
  }, [])

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setResult(null)
    setDrawnImage(null)
  }

  const handleConfigChange = (newConfig: { confThreshold: number; ocrDetThresh: number; unclipRatio: number }) => {
    setConfig(newConfig)
  }

  const handleClear = () => {
    setFile(null)
    setResult(null)
    setDrawnImage(null)
    setMarkdownContent(null)
    setMarkdownImageData(null)
    setError(null)
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('layout_conf_threshold', config.confThreshold.toString())
    formData.append('ocr_det_db_thresh', config.ocrDetThresh.toString())
    formData.append('unclip_ratio', config.unclipRatio.toString())

    try {
      // Fetch layout detection result
      const response = await fetch('/api/ppstructure', {
        method: 'POST',
        body: formData,
      })
      const analysisResult = await response.json()
      if (response.ok) {
        setResult(analysisResult.layout_regions || [])
      } else {
        setError(analysisResult.error || '上传失败')
      }

      // Fetch markdown content
      const markdownFormData = new FormData()
      markdownFormData.append('file', file)
      markdownFormData.append('analysis_result', JSON.stringify(analysisResult))
      const markdownResponse = await fetch('/api/ppstructure/markdown', {
        method: 'POST',
        body: markdownFormData,
      })
      if (markdownResponse.ok) {
        const markdownData = await markdownResponse.json()
        console.log('Markdown data received:', markdownData)
        console.log('Markdown content length:', markdownData.markdown?.length)
        console.log('Images count:', markdownData.images?.length)
        
        // 将图片数据转换为前端可用的格式
        const processedImages: { [key: string]: string } = {}
        if (markdownData.images && Array.isArray(markdownData.images)) {
          markdownData.images.forEach((img: any) => {
            if (img.filename && img.data) {
              // 后端已经返回base64编码的数据，直接使用
              processedImages[img.filename] = `data:image/png;base64,${img.data}`
            }
          })
        }
        
        setMarkdownContent(markdownData.markdown)
        setMarkdownImages(processedImages)
        console.log('Markdown content set with images:', Object.keys(processedImages))
      } else {
        console.error('Failed to fetch markdown content')
        setMarkdownContent('# Error\n\nFailed to generate markdown content.')
        setMarkdownImageData(null)
      }

      // Fetch drawn image
      const drawFormData = new FormData()
      drawFormData.append('file', file)
      drawFormData.append('analysis_result', JSON.stringify(analysisResult))
      const drawResponse = await fetch('/api/ppstructure/draw', {
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
      <ResultPanel result={result} imageFile={file} drawnImage={drawnImage} onMessage={setMessage} resultType="layout" viewOptions={['json', 'drawn-image', 'markdown']} markdownContent={markdownContent} markdownImageData={markdownImageData} markdownImages={markdownImages} />

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
                <code className="api-url">{apiBaseUrl}</code>
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
                    <li><code>layout_conf_threshold</code>: 布局检测阈值 (0.0-1.0，默认: 0.5)</li>
                    <li><code>ocr_det_db_thresh</code>: OCR检测阈值 (0.0-1.0，默认: 0.3)</li>
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

              <div className="api-section">
                <h4>📝 Markdown生成接口</h4>
                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ppstructure/markdown</code>
                </div>
                <div className="api-params">
                  <h5>参数：</h5>
                  <ul>
                    <li><code>file</code>: 原始图像文件</li>
                    <li><code>layout_result</code>: 布局检测结果的JSON字符串</li>
                  </ul>
                  <h5>返回：</h5>
                  <ul>
                    <li><code>markdown</code>: 生成的Markdown文档字符串（包含相对路径图片引用）</li>
                    <li><code>images</code>: 图片数组，每个图片包含 <code>filename</code> 和 <code>data</code>（二进制数据）</li>
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