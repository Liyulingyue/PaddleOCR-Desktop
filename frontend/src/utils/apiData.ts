export interface ApiEndpoint {
  id: string;
  title: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  path: string;
  description: string;
  params?: {
    name: string;
    description: string;
    type?: string;
    default?: string;
  }[];
  additionalInfo?: string[];
  examples: {
    lang: string;
    code: (baseUrl: string) => string;
  }[];
  responseTitle?: string;
  response?: string;
}

export interface ApiCategory {
  id: string;
  title: string;
  endpoints: ApiEndpoint[];
}

export const ocrApiData: ApiCategory[] = [
  {
    id: 'ocr-endpoints',
    title: 'OCR 识别接口',
    endpoints: [
      {
        id: 'ocr-basic',
        title: '📝 OCR 识别',
        method: 'POST',
        path: '/api/ocr/',
        description: '进行基础 OCR 识别，支持图像和 PDF 文件。',
        params: [
          { name: 'file', description: '上传的图像文件或PDF文件' },
          { name: 'det_db_thresh', description: '检测阈值 (0.0-1.0，默认: 0.3)', type: 'float', default: '0.3' },
          { name: 'cls_thresh', description: '分类阈值 (0.0-1.0，默认: 0.9)', type: 'float', default: '0.9' },
          { name: 'use_cls', description: '是否使用文本方向分类 (默认: true)', type: 'boolean', default: 'true' },
          { name: 'merge_overlaps', description: '是否合并重叠的文本框 (默认: false)', type: 'boolean', default: 'false' },
          { name: 'overlap_threshold', description: '合并重叠框的重叠度阈值 (默认: 0.9)', type: 'float', default: '0.9' },
        ],
        additionalInfo: [
          'PDF文件会被转换为高分辨率图像（300 DPI）进行OCR识别',
          '多页PDF会逐页处理，每页返回独立的OCR结果',
          '需要安装pymupdf库才能处理PDF文件',
          '如果PDF页面包含透明背景，会自动转换为RGB格式'
        ],
        examples: [
          {
            lang: 'cURL',
            code: (baseUrl) => `curl -X POST "${baseUrl}/api/ocr/" \\
  -F "file=@image.jpg" \\   # 或者 "file=@document.pdf"
  -F "det_db_thresh=0.3" \\
  -F "cls_thresh=0.9" \\
  -F "use_cls=true"`
          },
          {
            lang: 'Python',
            code: (baseUrl) => `import requests

url = "${baseUrl}/api/ocr/"
# 读取文件，支持图像 (jpg, png, etc.) 或 PDF
files = {'file': open('image.jpg', 'rb')} # 或 open('document.pdf', 'rb')
data = {
    'det_db_thresh': 0.3,
    'cls_thresh': 0.9,
    'use_cls': True
}
response = requests.post(url, files=files, data=data)
result = response.json()`
          }
        ],
        responseTitle: '图片/PDF 识别结果',
        response: `// 图片文件结果
{
  "results": [
    {
      "text": "识别的文本内容",
      "confidence": 0.95,
      "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
      "text_confidence": 0.95
    }
  ]
}

// PDF文件结果
{
  "file_type": "pdf",
  "total_pages": 3,
  "results": [
    {
      "page": 1,
      "results": [
        {
          "text": "页面1的文本",
          "confidence": 0.95,
          "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        }
      ]
    }
  ]
}`
      },
      {
        id: 'ocr-draw',
        title: '🎨 绘制结果',
        method: 'POST',
        path: '/api/ocr/draw',
        description: '在原始文件上绘制识别框。',
        params: [
          { name: 'file', description: '原始文件（用于确定文件类型）' },
          { name: 'ocr_result', description: 'OCR识别结果的JSON字符串' },
          { name: 'drop_score', description: '绘制阈值 (0.0-1.0，默认: 0.0)', type: 'float', default: '0.0' },
          { name: 'max_pages', description: '对于多页PDF，限制最多处理和返回的页面数 (默认: 2)', type: 'int', default: '2' },
        ],
        additionalInfo: [
          'PDF文件的每一页都会根据对应的OCR结果绘制识别框（不显示文字）',
          '返回每页的base64编码PNG图像',
          '如果某页没有有效的OCR结果，会返回原始页面图像',
          '多页PDF返回JSON格式的图片列表，包含处理统计信息'
        ],
        examples: [
          {
            lang: 'cURL',
            code: (baseUrl) => `curl -X POST "${baseUrl}/api/ocr/draw" \\
  -F "file=@document.pdf" \\
  -F "ocr_result={\\"results\\":[...]}" \\
  -F "drop_score=0.5"`
          },
          {
            lang: 'Python',
            code: (baseUrl) => `import requests, json, base64

# 先进行 OCR 识别
ocr_url = "${baseUrl}/api/ocr/"
files = {'file': open('image.jpg', 'rb')}
ocr_resp = requests.post(ocr_url, files=files)
ocr_result = ocr_resp.json()

# 再调用绘制接口
draw_url = "${baseUrl}/api/ocr/draw"
files = {'file': open('image.jpg', 'rb')}
data = {
    'ocr_result': json.dumps(ocr_result),
    'drop_score': 0.5
}
draw_resp = requests.post(draw_url, files=files, data=data)
draw_result = draw_resp.json()

# 保存返回的 base64 图像到本地文件
if 'images' in draw_result:
    for img in draw_result['images']:
        img_data = img['data'].split(',')[-1]
        with open(f"drawn_{img['page_number']}.png", 'wb') as f:
            f.write(base64.b64decode(img_data))
else:
    print('没有返回图像')`
          }
        ],
        responseTitle: '绘制图像返回结果',
        response: `{
  "file_type": "pdf",
  "total_pages": 3,
  "processed_pages": 2,
  "max_pages_limit": 2,
  "images": [
    {
      "page_number": 1,
      "data": "data:image/png;base64,..."
    }
  ]
}`
      },
      {
        id: 'ocr-to-text',
        title: '📄 OCR转文本',
        method: 'POST',
        path: '/api/ocr/ocr2text',
        description: '将结构化的OCR结果提取为纯文本。',
        params: [
          { name: 'ocr_result', description: 'OCR识别结果的JSON对象（请求体）' },
        ],
        additionalInfo: [
          '将结构化的OCR结果转换为纯文本格式',
          '自动提取每行识别的文本内容',
          '多页PDF的所有页面文本会连续合并'
        ],
        examples: [
          {
            lang: 'cURL',
            code: (baseUrl) => `curl -X POST "${baseUrl}/api/ocr/ocr2text" \\
  -H "Content-Type: application/json" \\
  -d '{"results": [{"text": "Hello World"}]}'`
          },
          {
            lang: 'Python',
            code: (baseUrl) => `import requests, json, base64

# 先执行 OCR 识别
ocr_url = "${baseUrl}/api/ocr/"
files = {'file': open('image.jpg', 'rb')}
ocr_resp = requests.post(ocr_url, files=files)
ocr_result = ocr_resp.json()
print("OCR 结果:", ocr_result)

# 绘制结果
draw_url = "${baseUrl}/api/ocr/draw"
files = {'file': open('image.jpg', 'rb')}
data = {'ocr_result': json.dumps(ocr_result), 'drop_score': 0.5}
draw_resp = requests.post(draw_url, files=files, data=data)
draw_result = draw_resp.json()
print("绘制返回:", draw_result)

# 将 OCR 输出转换为文本
text_url = "${baseUrl}/api/ocr/ocr2text"
response = requests.post(text_url, json=ocr_result)
text_output = response.json()
print("文本输出:", text_output["text"])

# 可选：保存绘制图片
if 'images' in draw_result:
    for img in draw_result['images']:
        img_data = img['data'].split(',')[-1]
        with open(f"drawn_{img['page_number']}.png", 'wb') as f:
            f.write(base64.b64decode(img_data))
`
          }
        ],
        response: `{ "text": "这是识别出的文本内容\\n第二行文本" }`
      }
    ]
  },
  {
    id: 'ocr-mgmt',
    title: '⚙️ 模型管理',
    endpoints: [
      {
        id: 'ocr-load',
        title: '加载模型',
        method: 'POST',
        path: '/api/ocr/load',
        description: '强制加载 OCR 模型（如果尚未加载）。返回成功或错误信息。',
        examples: [{ lang: 'cURL', code: (baseUrl) => `curl -X POST "${baseUrl}/api/ocr/load"` }]
      },
      {
        id: 'ocr-unload',
        title: '卸载模型',
        method: 'POST',
        path: '/api/ocr/unload',
        description: '卸载 OCR 模型并尝试释放资源（会将内存中的模型实例置空）。',
        examples: [{ lang: 'cURL', code: (baseUrl) => `curl -X POST "${baseUrl}/api/ocr/unload"` }]
      },
      {
        id: 'ocr-status',
        title: '模型状态',
        method: 'GET',
        path: '/api/ocr/model_status',
        description: '查询模型是否已加载，返回 JSON: { "loaded": true, "model_info": {...} }。',
        examples: [{ lang: 'cURL', code: (baseUrl) => `curl -X GET "${baseUrl}/api/ocr/model_status"` }],
        response: `{ "loaded": true, "message": "模型已加载" }`
      }
    ]
  }
];

export const ppStructureApiData: ApiCategory[] = [
  {
    id: 'pps-endpoints',
    title: 'PP-Structure 分析',
    endpoints: [
      {
        id: 'pps-basic',
        title: '📝 结构分析',
        method: 'POST',
        path: '/api/ppstructure/',
        description: '进行文档结构分析（返回 layout 格式）。',
        params: [
          { name: 'file', description: '上传的图像文件或PDF文件' },
          { name: 'ocr_det_db_thresh', description: 'OCR检测阈值', type: 'float', default: '0.3' },
          { name: 'unclip_ratio', description: '文本框扩大比例', type: 'float', default: '2.0' },
          { name: 'use_cls', description: '是否使用方向分类', type: 'boolean', default: 'true' },
          { name: 'merge_layout', description: '是否合并重叠的布局框', type: 'boolean', default: 'false' },
        ],
        additionalInfo: [
          'PDF文件会先转换为300 DPI图像再处理',
          '支持多页PDF逐页分析',
          '需要安装pymupdf支持'
        ],
        examples: [
          {
            lang: 'cURL',
            code: (baseUrl) => `curl -X POST "${baseUrl}/api/ppstructure/" -F "file=@doc.jpg" \\
             -F "ocr_det_db_thresh=0.3" \\
             -F "unclip_ratio=2.0"`
          },
          {
            lang: 'Python (基础调用)',
            code: (baseUrl) => `import requests

# 发起基础结构分析请求
files = {'file': open('doc.jpg', 'rb')} 
data = {'ocr_det_db_thresh': 0.3}

response = requests.post("${baseUrl}/api/ppstructure/", files=files, data=data)
result = response.json()
print(result) # 包含 layout_regions 及其 text}`
          }
        ],
        responseTitle: '分析结果格式',
        response: `{
  "layout_regions": [
    { "type": "text", "bbox": [x1, y1, x2, y2], "text": "识别内容", "confidence": 0.95 }
  ],
  "rotation": 0
}`
      },
      {
        id: 'pps-draw',
        title: '🎨 绘制结果',
        method: 'POST',
        path: '/api/ppstructure/draw',
        description: '绘制 PP-Structure 可视化结果。',
        params: [
          { name: 'file', description: '原始文件' },
          { name: 'analysis_result', description: '分析结果JSON字符串' },
          { name: 'page_number', description: '可视化指定页码 (针对单个导出)', type: 'int', default: '1' },
          { name: 'max_pages', description: '最大处理页数 (针对PDF)', type: 'int', default: '2' },
        ],
        examples: [
          { lang: 'cURL', code: (baseUrl) => `curl -X POST "${baseUrl}/api/ppstructure/draw" -F "file=@doc.pdf" -F "analysis_result=..."` },
          {
            lang: 'Python (分析+绘制)',
            code: (baseUrl) => `import requests
import json
import base64

# 1. 先进行分析
files = {'file': open('doc.jpg', 'rb')}
res = requests.post("${baseUrl}/api/ppstructure/", files=files)
analysis_result = res.json()

# 2. 将分析结果传给绘制接口
# 注意：analysis_result 必须序列化为 JSON 字符串
files_draw = {
    'file': open('doc.jpg', 'rb'),
    'analysis_result': (None, json.dumps(analysis_result))
}
draw_res = requests.post("${baseUrl}/api/ppstructure/draw", files=files_draw)
draw_data = draw_res.json()

# 保存结果
for page in draw_data.get('pages', []):
    img_data = base64.b64decode(page['image'].split(',')[-1])
    with open(f"result_{page['page_num']}.png", 'wb') as f:
        f.write(img_data)`
          }
        ]
      },
      {
        id: 'pps-markdown',
        title: '📝 Markdown生成',
        method: 'POST',
        path: '/api/ppstructure/markdown',
        description: '根据分析结果生成带图的 Markdown 文档。',
        params: [
          { name: 'file', description: '原始图像文件' },
          { name: 'analysis_result', description: '分析结果JSON字符串' },
        ],
        additionalInfo: [
          '返回包含 markdown 字符串和 base64 图像列表的对象',
          '图片文件名会自动与 markdown 内容对应'
        ],
        examples: [
          { lang: 'cURL', code: (baseUrl) => `curl -X POST "${baseUrl}/api/ppstructure/markdown" -F "file=@doc.jpg" -F "analysis_result=..."` },
          {
            lang: 'Python (分析+导出MD)',
            code: (baseUrl) => `import requests
import json
import base64

# 1. 先进行分析
files = {'file': open('doc.jpg', 'rb')}
res = requests.post("${baseUrl}/api/ppstructure/", files=files)
analysis_result = res.json()

# 2. 将分析结果传给 Markdown 接口
files_md = {
    'file': open('doc.jpg', 'rb'),
    'analysis_result': (None, json.dumps(analysis_result))
}
md_res = requests.post("${baseUrl}/api/ppstructure/markdown", files=files_md)
md_data = md_res.json()

# 保存 Markdown 和图片
with open("output.md", "w", encoding="utf8") as f:
    f.write(md_data['markdown'])

for img in md_data.get('images', []):
    with open(img['filename'], 'wb') as f:
        f.write(base64.b64decode(img['data']))`
          }
        ],
        response: `{
  "markdown": "# Header\\n...",
  "images": [ { "filename": "table_1.png", "data": "base64..." } ]
}`
      }
    ]
  },
  {
    id: 'pps-mgmt',
    title: '⚙️ 模型管理',
    endpoints: [
      {
        id: 'pps-load',
        title: '加载模型',
        method: 'POST',
        path: '/api/ppstructure/load',
        description: '强制加载 PP-Structure 模型。',
        examples: [{ lang: 'cURL', code: (baseUrl) => `curl -X POST "${baseUrl}/api/ppstructure/load"` }]
      },
      {
        id: 'pps-status',
        title: '模型状态',
        method: 'GET',
        path: '/api/ppstructure/model_status',
        description: '查询模型加载状态。',
        examples: [{ lang: 'cURL', code: (baseUrl) => `curl -X GET "${baseUrl}/api/ppstructure/model_status"` }]
      }
    ]
  }
];
