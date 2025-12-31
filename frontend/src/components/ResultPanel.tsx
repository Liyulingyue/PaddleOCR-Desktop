import { useState, useRef, useEffect } from 'react'

interface ResultPanelProps {
  result: any
  imageFile: File | null
  drawnImage: string | any[] | null
  onMessage: (message: string) => void
  resultType?: string
}

// 从OCR结果中提取纯文本
function extractTextFromResult(result: any, resultType: string = 'ocr'): string {
  if (!result) return ''
  
  if (resultType === 'layout') {
    // 布局检测结果
    if (Array.isArray(result)) {
      const layoutLines: string[] = []
      for (const region of result) {
        if (region && typeof region === 'object' && 'type' in region && 'bbox' in region) {
          const bbox = region.bbox
          const type = region.type
          const conf = region.confidence ? region.confidence.toFixed(3) : 'N/A'
          layoutLines.push(`${type}: [${bbox.join(', ')}] (conf: ${conf})`)
        }
      }
      return layoutLines.join('\n')
    }
    return ''
  }
  
  const textLines: string[] = []
  
  // 检查是否为多页PDF结果
  if (Array.isArray(result) && result.length > 0 && typeof result[0] === 'object' && 'page' in result[0]) {
    // 多页PDF结果 - pipeline格式
    for (const pageData of result) {
      const pageResults = pageData.results
      if (pageResults && Array.isArray(pageResults)) {
        for (const item of pageResults) {
          if (item && typeof item === 'object' && 'text' in item) {
            const text = item.text
            if (text && text.trim()) {
              textLines.push(text)
            }
          }
        }
      }
    }
  } else if (Array.isArray(result)) {
    // 单页结果 - pipeline格式
    for (const item of result) {
      if (item && typeof item === 'object' && 'text' in item) {
        const text = item.text
        if (text && text.trim()) {
          textLines.push(text)
        }
      }
    }
  }
  
  return textLines.join('\n')
}

function ResultPanel({ result, imageFile, drawnImage, onMessage, resultType = 'ocr' }: ResultPanelProps) {
  const [view, setView] = useState<'json' | 'drawn-image' | 'ocr-text'>('json')
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (view === 'ocr-text' && imageFile && result && canvasRef.current) {
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      const img = new Image()
      img.onload = () => {
        // 设置canvas尺寸
        canvas.width = img.width
        canvas.height = img.height

        // 填充白色背景作为空白画布
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, canvas.width, canvas.height)

        // 绘制OCR结果文字（如果有坐标信息）- 支持pipeline格式
        let ocrItems: any[] = []
        
        // 检查是否为多页PDF结果
        if (Array.isArray(result) && result.length > 0 && typeof result[0] === 'object' && 'page' in result[0]) {
          // 多页PDF，取第一页的结果
          ocrItems = result[0].results || []
        } else if (Array.isArray(result)) {
          // 单页结果
          ocrItems = result
        }

        if (ocrItems.length > 0) {
          ctx.strokeStyle = '#ff0000'
          ctx.lineWidth = 2
          ctx.fillStyle = '#000000'

          ocrItems.forEach((item: any) => {
            if (item && typeof item === 'object' && 'box' in item && 'text' in item) {
              const box = item.box
              const text = item.text
              
              if (Array.isArray(box) && box.length >= 4) {
                // 绘制边界框
                ctx.beginPath()
                if (box.length === 4) {
                  // 四边形框 [x1,y1,x2,y2,x3,y3,x4,y4]
                  ctx.moveTo(box[0], box[1])
                  ctx.lineTo(box[2], box[3])
                  ctx.lineTo(box[4], box[5])
                  ctx.lineTo(box[6], box[7])
                } else if (box.length === 8) {
                  // 展平的四边形
                  for (let i = 0; i < box.length; i += 2) {
                    if (i === 0) {
                      ctx.moveTo(box[i], box[i + 1])
                    } else {
                      ctx.lineTo(box[i], box[i + 1])
                    }
                  }
                }
                ctx.closePath()
                ctx.stroke()

                // 在框内绘制文本
                if (text && text.trim()) {
                  // 计算框的边界来绘制文字
                  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
                  
                  if (box.length === 4) {
                    // 四边形框
                    for (let i = 0; i < box.length; i += 2) {
                      minX = Math.min(minX, box[i])
                      minY = Math.min(minY, box[i + 1])
                      maxX = Math.max(maxX, box[i])
                      maxY = Math.max(maxY, box[i + 1])
                    }
                  } else if (box.length === 8) {
                    // 展平的四边形
                    for (let i = 0; i < box.length; i += 2) {
                      minX = Math.min(minX, box[i])
                      minY = Math.min(minY, box[i + 1])
                      maxX = Math.max(maxX, box[i])
                      maxY = Math.max(maxY, box[i + 1])
                    }
                  }
                  
                  const centerX = (minX + maxX) / 2
                  const centerY = (minY + maxY) / 2

                  // 调整字体大小基于框的高度
                  const boxHeight = maxY - minY
                  const fontSize = Math.max(12, Math.min(24, boxHeight * 0.8))
                  ctx.font = `${fontSize}px Arial`
                  ctx.textAlign = 'center'
                  ctx.textBaseline = 'middle'
                  
                  ctx.fillText(text, centerX, centerY)
                }
              }
            }
          })
        }
      }
      img.src = URL.createObjectURL(imageFile)
    }
  }, [view, imageFile, result])

  const copyResult = async () => {
    try {
      let contentToCopy: string
      
      if (view === 'ocr-text') {
        // 复制纯文本内容
        contentToCopy = extractTextFromResult(result, resultType)
      } else {
        // 复制JSON格式的结果
        contentToCopy = JSON.stringify(result || {}, null, 2)
      }
      
      await navigator.clipboard.writeText(contentToCopy)
      onMessage('已复制到剪贴板')
      setTimeout(() => onMessage(''), 2000) // 2秒后自动隐藏
    } catch (e) {
      onMessage('复制失败')
      setTimeout(() => onMessage(''), 2000)
    }
  }

  const downloadResult = () => {
    let content: string
    let filename: string
    let mimeType: string
    
    if (view === 'ocr-text') {
      // 下载纯文本内容
      content = extractTextFromResult(result, resultType)
      filename = resultType === 'layout' ? 'layout_result.txt' : 'ocr_result.txt'
      mimeType = 'text/plain'
    } else {
      // 下载JSON格式的结果
      content = JSON.stringify(result || {}, null, 2)
      filename = resultType === 'layout' ? 'layout_result.json' : 'ocr_result.json'
      mimeType = 'application/json'
    }
    
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <aside className="result-panel">
      <div className="result-panel-header">
        <h3>解析结果</h3>
        <div className="header-controls">
          <div className="action-buttons">
            <button className="action-btn copy-btn" onClick={copyResult} title="复制结果">📋复制</button>
            <button className="action-btn download-btn" onClick={downloadResult} title="下载结果">💾下载</button>
          </div>
          <label htmlFor="view-select" className="sr-only">结果格式</label>
          <select
            id="view-select"
            className="view-select"
            value={view}
            onChange={(e) => setView(e.target.value as 'json' | 'drawn-image' | 'ocr-text')}
          >
            <option value="json">JSON</option>
            <option value="drawn-image">绘制图像</option>
            {resultType !== 'layout' && <option value="ocr-text">纯文本</option>}
          </select>
        </div>
      </div>

      <div className="result-body">
        {result ? (
          view === 'json' ? (
            <pre>{JSON.stringify(result, null, 2)}</pre>
          ) : view === 'ocr-text' ? (
            <div className="ocr-text">
              <pre>{extractTextFromResult(result, resultType)}</pre>
            </div>
          ) : (
            <div className="drawn-image">
              {drawnImage ? (
                Array.isArray(drawnImage) ? (
                  // 多张图片（PDF文件）
                  <div className="pdf-images">
                    {drawnImage.map((pageData: any, index: number) => (
                      <div key={index} className="pdf-page">
                        <div className="page-header">第 {pageData.page} 页</div>
                        <img 
                          src={pageData.image} 
                          alt={`OCR结果绘制 - 第${pageData.page}页`} 
                          style={{ maxWidth: '100%', height: 'auto' }} 
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  // 单张图片（普通图像文件）
                  <img src={drawnImage} alt="OCR结果绘制" style={{ maxWidth: '100%', height: 'auto' }} />
                )
              ) : (
                <p>绘制图像加载中...</p>
              )}
            </div>
          )
        ) : (
          <div className="empty-state">
            <p>尚无解析结果</p>
          </div>
        )}
      </div>
    </aside>
  )
}

export default ResultPanel