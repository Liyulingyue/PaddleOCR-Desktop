import { useState, useEffect } from 'react'
import ControlBar from '../components/ControlBar'
import Viewer from '../components/Viewer'
import ResultPanel from '../components/ResultPanel'
import { getCachedApiBaseUrl } from '../utils/api'

function OCRV5Page() {
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

  // 自动清除全局消息（例如：加载/卸载提示）
  useEffect(() => {
    if (!message) return
    const timer = setTimeout(() => setMessage(null), 1000)
    return () => clearTimeout(timer)
  }, [message, setMessage])

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

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)

    try {
      // 获取API基础URL
      const apiBaseUrl = await getCachedApiBaseUrl()

      const formData = new FormData()
      formData.append('file', file)
      formData.append('det_db_thresh', config.detThresh.toString())
      formData.append('cls_thresh', config.clsThresh.toString())
      formData.append('use_cls', config.useCls.toString())

      // Fetch OCR result
      const response = await fetch(`${apiBaseUrl}/api/ocr`, {
        method: 'POST',
        body: formData,
      })
      const data = await response.json()
      if (response.ok) {
        setResult(data.results || data.result)
      } else {
        setError(data.error || '上传失败')
      }

      // Fetch drawn image
      const drawFormData = new FormData()
      drawFormData.append('file', file)
      drawFormData.append('ocr_result', JSON.stringify(data))
      drawFormData.append('drop_score', config.dropScore.toString())
      const drawResponse = await fetch(`${apiBaseUrl}/api/ocr/draw`, {
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
    <div className={`layout ${result ? '' : 'no-result'}`}>
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
        apiBaseUrl={apiBaseUrl}
        onMessage={setMessage}
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
                <code className="api-url">{apiBaseUrl}</code>
                <p className="api-note">API路径会自动转发到后端服务器</p>
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
                  <h5>PDF文件处理说明：</h5>
                  <ul>
                    <li>PDF文件会被转换为高分辨率图像（300 DPI）进行OCR识别</li>
                    <li>多页PDF会逐页处理，每页返回独立的OCR结果</li>
                    <li>需要安装pymupdf库才能处理PDF文件</li>
                    <li>如果PDF页面包含透明背景，会自动转换为RGB格式</li>
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
                  <h5>PDF文件处理说明：</h5>
                  <ul>
                    <li>PDF文件的每一页都会根据对应的OCR结果绘制识别框和文本</li>
                    <li>返回每页的base64编码PNG图像</li>
                    <li>如果某页没有有效的OCR结果，会返回原始页面图像</li>
                  </ul>
                </div>
              </div>

              <div className="api-section">
                <h4>� OCR转文本接口</h4>
                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ocr/ocr2text</code>
                </div>
                <div className="api-params">
                  <h5>参数：</h5>
                  <ul>
                    <li><code>ocr_result</code>: OCR识别结果的JSON对象（请求体）</li>
                  </ul>
                  <h5>功能说明：</h5>
                  <ul>
                    <li>将结构化的OCR结果转换为纯文本格式</li>
                    <li>自动提取每行识别的文本内容</li>
                    <li>多页PDF的所有页面文本会连续合并</li>
                  </ul>
                </div>
              </div>

              <div className="api-section">
                <h4>⚙️ 模型状态接口</h4>
                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ocr/load</code>
                </div>
                <div className="api-params">
                  <h5>说明：</h5>
                  <ul>
                    <li>强制加载 OCR 模型（如果尚未加载）。返回成功或错误信息。</li>
                  </ul>
                  <h5>示例（curl）：</h5>
                  <pre>{`curl -X POST ${apiBaseUrl}/api/ocr/load`}</pre>
                </div>

                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ocr/unload</code>
                </div>
                <div className="api-params">
                  <h5>说明：</h5>
                  <ul>
                    <li>卸载 OCR 模型并尝试释放资源（会将内存中的模型实例置空）。</li>
                  </ul>
                  <h5>示例（curl）：</h5>
                  <pre>{`curl -X POST ${apiBaseUrl}/api/ocr/unload`}</pre>
                </div>

                <div className="api-endpoint">
                  <code className="method">GET</code>
                  <code className="endpoint">/api/ocr/model_status</code>
                </div>
                <div className="api-params">
                  <h5>说明：</h5>
                  <ul>
                    <li>查询模型是否已加载，返回 JSON: <code>{`{ "loaded": true }`}</code> 或 <code>{`{ "loaded": false }`}</code></li>
                  </ul>
                  <h5>示例（curl）：</h5>
                  <pre>{`curl ${apiBaseUrl}/api/ocr/model_status`}</pre>

                  <h5>示例（JavaScript / fetch）：</h5>
                  <pre>{`// 查询模型状态
fetch("${apiBaseUrl}/api/ocr/model_status")
  .then(res => res.json())
  .then(j => console.log('loaded:', j.loaded))
  .catch(err => console.error(err))

// 加载模型
fetch("${apiBaseUrl}/api/ocr/load", { method: 'POST' })
  .then(res => res.ok ? console.log('加载成功') : res.text().then(t => console.error(t)))
  .catch(err => console.error(err))

// 卸载模型
fetch("${apiBaseUrl}/api/ocr/unload", { method: 'POST' })
  .then(res => res.ok ? console.log('卸载成功') : res.text().then(t => console.error(t)))
  .catch(err => console.error(err))`}</pre>
                </div>
              </div>

              <div className="api-section">
                <h4>�🐍 Python 调用示例</h4>
                <div className="code-example">
                  <pre>{`import requests
import json

# OCR识别示例
def ocr_file(file_path, api_base_url="${apiBaseUrl}"):
    url = f"{api_base_url}/api/ocr"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {{
            'det_db_thresh': '0.3',
            'cls_thresh': '0.9', 
            'use_cls': 'true'
        }}
        response = requests.post(url, files=files, data=data)
        return response.json()

# 绘制结果示例  
def draw_ocr_result(file_path, ocr_result, api_base_url="${apiBaseUrl}"):
    url = f"{api_base_url}/api/ocr/draw"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {{
            'ocr_result': json.dumps(ocr_result),
            'drop_score': '0.5'
        }}
        response = requests.post(url, files=files, data=data)
        
        # 检查响应类型
        content_type = response.headers.get('content-type', '')
        
        if content_type.startswith('image/'):
            # 单张图片（用于普通图像文件）
            with open('result.png', 'wb') as f:
                f.write(response.content)
            print("结果已保存为 result.png")
        else:
            # JSON响应（用于PDF文件，返回多页base64图片）
            result = response.json()
            if 'result' in result and isinstance(result['result'], list):
                for page_data in result['result']:
                    page_num = page_data.get('page', 'unknown')
                    image_data = page_data.get('image', '')
                    if image_data.startswith('data:image/png;base64,'):
                        # 保存每页图片
                        import base64
                        image_bytes = base64.b64decode(image_data.split(',')[1])
                        filename = f'result_page_{page_num}.png'
                        with open(filename, 'wb') as f:
                            f.write(image_bytes)
                        print(f"第{page_num}页结果已保存为 {filename}")
            else:
                print("绘制结果处理失败")

# OCR结果转文本示例
def ocr_result_to_text(ocr_result, api_base_url="${apiBaseUrl}"):
    url = f"{api_base_url}/api/ocr/ocr2text"
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=ocr_result, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"错误: {response.status_code}, {response.text}")
        return None

# 模型加载 / 卸载 / 查询 示例
def load_model(api_base_url="${apiBaseUrl}"):
    url = f"{api_base_url}/api/ocr/load"
    resp = requests.post(url)
    if resp.ok:
        print("模型加载成功")
    else:
        print("模型加载失败:", resp.status_code, resp.text)


def unload_model(api_base_url="${apiBaseUrl}"):
    url = f"{api_base_url}/api/ocr/unload"
    resp = requests.post(url)
    if resp.ok:
        print("模型卸载成功")
    else:
        print("模型卸载失败:", resp.status_code, resp.text)


def model_status(api_base_url="${apiBaseUrl}"):
    url = f"{api_base_url}/api/ocr/model_status"
    resp = requests.get(url)
    if resp.ok:
        j = resp.json()
        print("loaded:", j.get('loaded'))
        return j.get('loaded')
    else:
        print("查询失败:", resp.status_code, resp.text)
        return None

# 使用示例
if __name__ == "__main__":
    # 识别图片文件
    result = ocr_file("example.jpg")
    print("OCR结果:", json.dumps(result, indent=2, ensure_ascii=False))
    
    # 将OCR结果转换为纯文本
    text_result = ocr_result_to_text(result)
    if text_result:
        print("提取的文本:", text_result['text'])
    
    # 模型控制示例
    print("模型状态:", model_status())
    print("正在加载模型...")
    load_model()
    print("模型状态:", model_status())
    print("正在卸载模型...")
    unload_model()
    print("模型状态:", model_status())

    # 识别PDF文件
    pdf_result = ocr_file("document.pdf")
    print("PDF OCR结果:", json.dumps(pdf_result, indent=2, ensure_ascii=False))
    
    # 将PDF OCR结果转换为纯文本
    pdf_text_result = ocr_result_to_text(pdf_result)
    if pdf_text_result:
        print("PDF文本:", pdf_text_result['text'])
    
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

                  <h5>OCR转文本结果：</h5>
                  <pre>{`{
  "text": "这是识别出的文本内容\\n第二行文本\\n第三行文本\\n第二页的文本内容\\n第二行\\n第三行"
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

export default OCRV5Page