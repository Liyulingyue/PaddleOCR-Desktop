import React from 'react'

interface ApiModalProps {
  isOpen: boolean
  onClose: () => void
  apiBaseUrl: string
  type: 'ocr' | 'ppstructure'
}

const ApiModal: React.FC<ApiModalProps> = ({ isOpen, onClose, apiBaseUrl, type }) => {
  if (!isOpen) return null

  const renderOCRContent = () => (
    <>
      <div className="api-section">
        <h4>📝 OCR 识别接口</h4>
        <div className="api-endpoint">
          <code className="method">POST</code>
          <code className="endpoint">/api/ocr/</code>
        </div>
        <div className="api-params">
          <h5>参数：</h5>
          <ul>
            <li><code>file</code>: 上传的图像文件或PDF文件</li>
            <li><code>det_db_thresh</code>: 检测阈值 (0.0-1.0，默认: 0.3)</li>
            <li><code>cls_thresh</code>: 分类阈值 (0.0-1.0，默认: 0.9)</li>
            <li><code>use_cls</code>: 是否使用文本方向分类 (true/false，默认: true)</li>
            <li><code>merge_overlaps</code>: 是否合并重叠的文本框 (true/false，默认: false)</li>
            <li><code>overlap_threshold</code>: 合并重叠框的重叠度阈值 (0.0-1.0，默认: 0.9)</li>
          </ul>
          <h5>PDF文件处理说明：</h5>
          <ul>
            <li>PDF文件会被转换为高分辨率图像（300 DPI）进行OCR识别</li>
            <li>多页PDF会逐页处理，每页返回独立的OCR结果</li>
            <li>需要安装pymupdf库才能处理PDF文件</li>
            <li>如果PDF页面包含透明背景，会自动转换为RGB格式</li>
          </ul>
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X POST "${apiBaseUrl}/api/ocr/" \\
  -F "file=@image.jpg" \\
  -F "det_db_thresh=0.3" \\
  -F "cls_thresh=0.9" \\
  -F "use_cls=true"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests

url = "${apiBaseUrl}/api/ocr/"
files = {'file': open('image.jpg', 'rb')}
data = {
    'det_db_thresh': 0.3,
    'cls_thresh': 0.9,
    'use_cls': True
}
response = requests.post(url, files=files, data=data)
result = response.json()`}</pre>
          </div>
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
            <li><code>drop_score</code>: 绘制阈值 (0.0-1.0，默认: 0.0，0.0表示不过滤)</li>
            <li><code>max_pages</code>: 对于多页PDF，限制最多处理和返回的页面数 (默认: 2)</li>
          </ul>
          <h5>PDF文件处理说明：</h5>
          <ul>
            <li>PDF文件的每一页都会根据对应的OCR结果绘制识别框（不显示文字）</li>
            <li>返回每页的base64编码PNG图像</li>
            <li>如果某页没有有效的OCR结果，会返回原始页面图像</li>
            <li>多页PDF返回JSON格式的图片列表，包含处理统计信息</li>
          </ul>
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X POST "${apiBaseUrl}/api/ocr/draw" \\
  -F "file=@document.pdf" \\
  -F "ocr_result={\\"results\\":[{\\"text\\":\\"Hello\\",\\"bbox\\":[[10,10],[100,10],[100,50],[10,50]]}]}" \\
  -F "drop_score=0.5"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests
import json

url = "${apiBaseUrl}/api/ocr/draw"
files = {'file': open('document.pdf', 'rb')}
data = {
    'ocr_result': json.dumps(ocr_result),  # OCR结果JSON字符串
    'drop_score': 0.5
}
response = requests.post(url, files=files, data=data)
result = response.json()`}</pre>
          </div>
        </div>
      </div>

      <div className="api-section">
        <h4>📄 OCR转文本接口</h4>
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
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X POST "${apiBaseUrl}/api/ocr/ocr2text" \\
  -H "Content-Type: application/json" \\
  -d '{
    "results": [
      {"text": "Hello World", "confidence": 0.95},
      {"text": "Second line", "confidence": 0.89}
    ]
  }'`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests

url = "${apiBaseUrl}/api/ocr/ocr2text"
ocr_result = {
    "results": [
        {"text": "Hello World", "confidence": 0.95},
        {"text": "Second line", "confidence": 0.89}
    ]
}
response = requests.post(url, json=ocr_result)
text_result = response.json()`}</pre>
          </div>
        </div>
      </div>

      <div className="api-section">
        <h4>⚙️ 模型管理接口</h4>
        <div className="api-endpoint">
          <code className="method">POST</code>
          <code className="endpoint">/api/ocr/load</code>
        </div>
        <div className="api-params">
          <h5>说明：</h5>
          <ul>
            <li>强制加载 OCR 模型（如果尚未加载）。返回成功或错误信息。</li>
          </ul>
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X POST "${apiBaseUrl}/api/ocr/load"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests

url = "${apiBaseUrl}/api/ocr/load"
response = requests.post(url)
result = response.json()`}</pre>
          </div>
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
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X POST "${apiBaseUrl}/api/ocr/unload"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests

url = "${apiBaseUrl}/api/ocr/unload"
response = requests.post(url)
result = response.json()`}</pre>
          </div>
        </div>

        <div className="api-endpoint">
          <code className="method">GET</code>
          <code className="endpoint">/api/ocr/model_status</code>
        </div>
        <div className="api-params">
          <h5>说明：</h5>
          <ul>
            <li>查询模型是否已加载，返回 JSON: <code>{`{ "loaded": true, "model_info": {...} }`}</code></li>
          </ul>
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X GET "${apiBaseUrl}/api/ocr/model_status"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests

url = "${apiBaseUrl}/api/ocr/model_status"
response = requests.get(url)
status = response.json()`}</pre>
          </div>
        </div>
      </div>

      <div className="api-section">
        <h4>📋 返回格式</h4>
        <div className="response-examples">
          <h5>图片文件OCR结果：</h5>
          <pre>{`{
  "results": [
    {
      "text": "识别的文本内容",
      "confidence": 0.95,
      "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
      "text_confidence": 0.95
    }
  ]
}`}</pre>

          <h5>PDF文件OCR结果：</h5>
          <pre>{`{
  "file_type": "pdf",
  "total_pages": 3,
  "results": [
    {
      "page": 1,
      "results": [
        {
          "text": "页面1的文本",
          "confidence": 0.95,
          "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
          "text_confidence": 0.95,
          "rotation": 0
        }
      ]
    }
  ]
}`}</pre>

          <h5>PDF绘制结果：</h5>
          <pre>{`{
  "file_type": "pdf",
  "total_pages": 3,
  "processed_pages": 2,
  "max_pages_limit": 2,
  "images": [
    {
      "page_number": 1,
      "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    }
  ]
}`}</pre>

          <h5>OCR转文本结果：</h5>
          <pre>{`{
  "text": "这是识别出的文本内容\\n第二行文本\\n第三行文本"
}`}</pre>
        </div>
      </div>
    </>
  )

  const renderPPStructureContent = () => (
    <>
      <div className="api-section">
        <h4>📝 PP-Structure 分析接口</h4>
        <div className="api-endpoint">
          <code className="method">POST</code>
          <code className="endpoint">/api/ppstructure/</code>
        </div>
        <div className="api-params">
          <h5>参数：</h5>
          <ul>
            <li><code>file</code>: 上传的图像文件或PDF文件</li>
            <li><code>ocr_det_db_thresh</code>: OCR检测阈值 (0.0-1.0，默认: 0.3)</li>
            <li><code>unclip_ratio</code>: 文本框扩大比例 (默认: 2.0)</li>
            <li><code>merge_overlaps</code>: 是否合并重叠框 (true/false，默认: false)</li>
            <li><code>overlap_threshold</code>: 重叠阈值 (0.0-1.0，默认: 0.9)</li>
            <li><code>merge_layout</code>: 是否合并布局 (true/false，默认: false)</li>
            <li><code>layout_overlap_threshold</code>: 布局重叠阈值 (0.0-1.0，默认: 0.9)</li>
            <li><code>use_cls</code>: 是否使用方向分类 (true/false，默认: true)</li>
            <li><code>cls_thresh</code>: 分类阈值 (0.0-1.0，默认: 0.9)</li>
          </ul>
          <h5>PDF文件处理说明：</h5>
          <ul>
            <li>PDF文件会被转换为高分辨率图像（300 DPI）进行结构分析</li>
            <li>多页PDF会逐页处理，每页返回独立的结构分析结果</li>
            <li>需要安装pymupdf库才能处理PDF文件</li>
          </ul>
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X POST "${apiBaseUrl}/api/ppstructure/" \\
  -F "file=@document.jpg" \\
  -F "ocr_det_db_thresh=0.3" \\
  -F "use_cls=true" \\
  -F "cls_thresh=0.9"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests

url = "${apiBaseUrl}/api/ppstructure/"
files = {'file': open('document.jpg', 'rb')}
data = {
    'ocr_det_db_thresh': 0.3,
    'use_cls': True,
    'cls_thresh': 0.9
}
response = requests.post(url, files=files, data=data)
result = response.json()`}</pre>
          </div>
        </div>
      </div>

      <div className="api-section">
        <h4>🎨 绘制结果接口</h4>
        <div className="api-endpoint">
          <code className="method">POST</code>
          <code className="endpoint">/api/ppstructure/draw</code>
        </div>
        <div className="api-params">
          <h5>参数：</h5>
          <ul>
            <li><code>file</code>: 原始文件（用于确定文件类型）</li>
            <li><code>analysis_result</code>: 结构分析结果的JSON字符串</li>
            <li><code>page_number</code>: 对于单页PDF的可视化指定页码 (默认: 1)</li>
            <li><code>max_pages</code>: 对于多页PDF，限制最多处理和返回的页面数 (默认: 2)</li>
          </ul>
          <h5>PDF文件处理说明：</h5>
          <ul>
            <li>PDF文件的每一页都会根据对应的结构分析结果绘制可视化</li>
            <li>返回每页的base64编码PNG图像</li>
            <li>多页PDF返回JSON格式的图片列表，包含处理统计信息</li>
          </ul>
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X POST "${apiBaseUrl}/api/ppstructure/draw" \\
  -F "file=@document.pdf" \\
  -F "analysis_result={\\"layout_regions\\":[{\\"type\\":\\"text\\",\\"bbox\\":[10,10,200,50]}]}" \\
  -F "max_pages=2"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests
import json

url = "${apiBaseUrl}/api/ppstructure/draw"
files = {'file': open('document.pdf', 'rb')}
data = {
    'analysis_result': json.dumps(analysis_result),  # 结构分析结果JSON字符串
    'max_pages': 2
}
response = requests.post(url, files=files, data=data)
result = response.json()`}</pre>
          </div>
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
            <li><code>analysis_result</code>: 结构分析结果的JSON字符串</li>
          </ul>
          <h5>返回：</h5>
          <ul>
            <li><code>markdown</code>: 生成的Markdown文档字符串</li>
            <li><code>images</code>: 图片数组，每个图片包含 <code>filename</code> 和 <code>data</code>（base64编码）</li>
          </ul>
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X POST "${apiBaseUrl}/api/ppstructure/markdown" \\
  -F "file=@document.jpg" \\
  -F "analysis_result={\\"layout_regions\\":[{\\"type\\":\\"text\\",\\"text\\":\\"Hello World\\"}]}"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests
import json

url = "${apiBaseUrl}/api/ppstructure/markdown"
files = {'file': open('document.jpg', 'rb')}
data = {
    'analysis_result': json.dumps(analysis_result)  # 结构分析结果JSON字符串
}
response = requests.post(url, files=files, data=data)
markdown_result = response.json()`}</pre>
          </div>
        </div>
      </div>

      <div className="api-section">
        <h4>⚙️ 模型管理接口</h4>
        <div className="api-endpoint">
          <code className="method">POST</code>
          <code className="endpoint">/api/ppstructure/load</code>
        </div>
        <div className="api-params">
          <h5>说明：</h5>
          <ul>
            <li>强制加载 PP-Structure 模型（如果尚未加载）。</li>
          </ul>
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X POST "${apiBaseUrl}/api/ppstructure/load"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests

url = "${apiBaseUrl}/api/ppstructure/load"
response = requests.post(url)
result = response.json()`}</pre>
          </div>
        </div>

        <div className="api-endpoint">
          <code className="method">POST</code>
          <code className="endpoint">/api/ppstructure/unload</code>
        </div>
        <div className="api-params">
          <h5>说明：</h5>
          <ul>
            <li>卸载 PP-Structure 模型并释放资源。</li>
          </ul>
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X POST "${apiBaseUrl}/api/ppstructure/unload"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests

url = "${apiBaseUrl}/api/ppstructure/unload"
response = requests.post(url)
result = response.json()`}</pre>
          </div>
        </div>

        <div className="api-endpoint">
          <code className="method">GET</code>
          <code className="endpoint">/api/ppstructure/model_status</code>
        </div>
        <div className="api-params">
          <h5>说明：</h5>
          <ul>
            <li>查询模型是否已加载，返回 JSON: <code>{`{ "loaded": true, "model_info": {...} }`}</code></li>
          </ul>
        </div>
        <div className="code-examples">
          <h5>使用示例：</h5>
          <div className="code-block">
            <h6>cURL:</h6>
            <pre>{`curl -X GET "${apiBaseUrl}/api/ppstructure/model_status"`}</pre>
          </div>
          <div className="code-block">
            <h6>Python:</h6>
            <pre>{`import requests

url = "${apiBaseUrl}/api/ppstructure/model_status"
response = requests.get(url)
status = response.json()`}</pre>
          </div>
        </div>
      </div>

      <div className="api-section">
        <h4>📋 返回格式</h4>
        <div className="response-examples">
          <h5>图片文件结构分析结果：</h5>
          <pre>{`{
  "layout_regions": [
    {
      "type": "text",
      "bbox": [x1, y1, x2, y2],
      "text": "识别的文本内容",
      "confidence": 0.95
    }
  ],
  "rotation": 0
}`}</pre>

          <h5>PDF文件结构分析结果：</h5>
          <pre>{`{
  "file_type": "pdf",
  "total_pages": 3,
  "pages": [
    {
      "page_number": 1,
      "layout_regions": [
        {
          "type": "text",
          "bbox": [x1, y1, x2, y2],
          "text": "页面1的文本",
          "confidence": 0.95
        }
      ],
      "rotation": 0
    }
  ]
}`}</pre>

          <h5>PDF绘制结果：</h5>
          <pre>{`{
  "file_type": "pdf",
  "total_pages": 3,
  "processed_pages": 2,
  "max_pages_limit": 2,
  "images": [
    {
      "page_number": 1,
      "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    }
  ]
}`}</pre>

          <h5>Markdown生成结果：</h5>
          <pre>{`{
  "markdown": "# 文档标题\\n\\n文档内容...",
  "images": [
    {
      "filename": "table_1.png",
      "data": "base64编码的图片数据"
    }
  ]
}`}</pre>
        </div>
      </div>
    </>
  )

  return (
    <div className="api-modal-overlay" onClick={onClose}>
      <div className="api-modal" onClick={(e) => e.stopPropagation()}>
        <div className="api-modal-header">
          <h3>API 文档</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="api-modal-content">
          <div className="api-section">
            <h4>🔗 接口地址</h4>
            <code className="api-url">{apiBaseUrl}</code>
            <p className="api-note">API路径会自动转发到后端服务器</p>
          </div>

          {type === 'ocr' ? renderOCRContent() : renderPPStructureContent()}
        </div>
      </div>
    </div>
  )
}

export default ApiModal