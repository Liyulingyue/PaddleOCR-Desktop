import { useState } from 'react'
import ControlBar from '../components/ControlBar'
import Viewer from '../components/Viewer'
import ResultPanel from '../components/ResultPanel'

function OCRV4Page() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<any>(null)
  const [drawnImage, setDrawnImage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState({ 
    dropScore: 0.5,
    detThresh: 0.3,
    clsThresh: 0.9,
    useCls: true
  })
  const [message, setMessage] = useState<string | null>(null)
  const [showApiModal, setShowApiModal] = useState(false)

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setResult(null)
    setDrawnImage(null)
  }

  const handleConfigChange = (newConfig: { 
    dropScore: number
    detThresh: number
    clsThresh: number
    useCls: boolean
  }) => {
    setConfig(newConfig)
  }

  const handleClear = () => {
    setFile(null)
    setResult(null)
    setDrawnImage(null)
    setError(null)
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('det_db_thresh', config.detThresh.toString())
    formData.append('cls_thresh', config.clsThresh.toString())
    formData.append('use_cls', config.useCls.toString())

    try {
      // Fetch OCR result
      const response = await fetch('http://localhost:8000/api/ocr', {
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
      drawFormData.append('ocr_result', JSON.stringify(data))
      drawFormData.append('drop_score', config.dropScore.toString())
      const drawResponse = await fetch('http://localhost:8000/api/ocr/draw', {
        method: 'POST',
        body: drawFormData,
      })
      if (drawResponse.ok) {
        const contentType = drawResponse.headers.get('content-type')
        if (contentType && contentType.startsWith('image/')) {
          // 单张图片（用于普通图像文件）
          const blob = await drawResponse.blob()
          const imageUrl = URL.createObjectURL(blob)
          setDrawnImage(imageUrl)
        } else {
          // 多张图片（用于PDF文件）
          const drawData = await drawResponse.json()
          if (drawData.result && Array.isArray(drawData.result)) {
            // 将多张图片拼接成一个大的base64字符串数组
            setDrawnImage(drawData.result)
          }
        }
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
      />
      <Viewer file={file} />
      <ResultPanel result={result} imageFile={file} drawnImage={drawnImage} onMessage={setMessage} />

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
                <h4>📝 OCR 识别接口</h4>
                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ocr</code>
                </div>
                <div className="api-params">
                  <h5>参数：</h5>
                  <ul>
                    <li><code>file</code>: 上传的文件（支持图片和PDF）</li>
                    <li><code>det_db_thresh</code>: 检测阈值 (0.0-1.0，默认: 0.3)</li>
                    <li><code>cls_thresh</code>: 分类阈值 (0.0-1.0，默认: 0.9)</li>
                    <li><code>use_cls</code>: 是否使用文本方向分类 (true/false，默认: true)</li>
                  </ul>
                </div>
              </div>

              <div className="api-section">
                <h4>🎨 绘制结果接口</h4>
                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ocr/draw</code>
                </div>
                <div className="api-params">
                  <h5>参数：</h5>
                  <ul>
                    <li><code>file</code>: 原始文件（用于确定文件类型）</li>
                    <li><code>ocr_result</code>: OCR识别结果的JSON字符串</li>
                    <li><code>drop_score</code>: 绘制阈值 (0.0-1.0，默认: 0.5)</li>
                  </ul>
                </div>
              </div>

              <div className="api-section">
                <h4>🐍 Python 调用示例</h4>
                <div className="code-example">
                  <pre>{`import requests

# OCR识别示例
def ocr_image(file_path):
    url = "http://localhost:8000/api/ocr"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'det_db_thresh': '0.3',
            'cls_thresh': '0.9', 
            'use_cls': 'true'
        }
        response = requests.post(url, files=files, data=data)
        return response.json()

# 绘制结果示例  
def draw_ocr_result(file_path, ocr_result):
    url = "http://localhost:8000/api/ocr/draw"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'ocr_result': json.dumps(ocr_result),
            'drop_score': '0.5'
        }
        response = requests.post(url, files=files, data=data)
        
        # 对于图片文件，返回PNG图片
        if response.headers.get('content-type', '').startswith('image/'):
            with open('result.png', 'wb') as f:
                f.write(response.content)
        # 对于PDF文件，返回JSON格式的多页图片
        else:
            result = response.json()
            # result['result'] 包含每页的base64图片数据

# 使用示例
if __name__ == "__main__":
    # 识别图片
    result = ocr_image("example.jpg")
    print("OCR结果:", result)
    
    # 绘制结果
    draw_ocr_result("example.jpg", result)`}</pre>
                </div>
              </div>

              <div className="api-section">
                <h4>📋 返回格式</h4>
                <div className="response-examples">
                  <h5>图片文件OCR结果：</h5>
                  <pre>{`{
  "result": [
    [
      [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],  // 文本框坐标
      ["识别文本", 0.95]  // 文本内容和置信度
    ],
    ...
  ]
}`}</pre>

                  <h5>PDF文件OCR结果：</h5>
                  <pre>{`{
  "result": [
    {
      "page": 1,
      "result": [
        [
          [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
          ["识别文本", 0.95]
        ],
        ...
      ]
    },
    ...
  ]
}`}</pre>

                  <h5>PDF绘制结果：</h5>
                  <pre>{`{
  "result": [
    {
      "page": 1,
      "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    },
    ...
  ]
}`}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default OCRV4Page
