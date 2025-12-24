import { useState, useRef, useEffect } from 'react'

interface ResultPanelProps {
  result: any
  imageFile: File | null
  drawnImage: string | any[] | null
  onMessage: (message: string) => void
}

// 从OCR结果中提取纯文本
function extractTextFromResult(result: any): string {
  if (!result) return ''
  
  const resultData = result
  const textLines: string[] = []
  
  // 检查是否为多页PDF结果
  if (Array.isArray(resultData) && resultData.length > 0 && typeof resultData[0] === 'object' && 'page' in resultData[0]) {
    // 多页PDF结果
    for (const pageData of resultData) {
      const pageResult = pageData.result
      if (pageResult && Array.isArray(pageResult) && pageResult.length > 0) {
        // 提取该页的所有文本行
        for (const line of pageResult[0] || []) {
          if (Array.isArray(line) && line.length >= 2) {
            const text = Array.isArray(line[1]) && line[1].length >= 1 ? line[1][0] : ''
            if (text && text.trim()) {
              textLines.push(text)
            }
          }
        }
      }
    }
  } else {
    // 单页图像结果
    if (Array.isArray(resultData) && resultData.length > 0) {
      for (const line of resultData[0] || []) {
        if (Array.isArray(line) && line.length >= 2) {
          const text = Array.isArray(line[1]) && line[1].length >= 1 ? line[1][0] : ''
          if (text && text.trim()) {
            textLines.push(text)
          }
        }
      }
    }
  }
  
  return textLines.join('\n')
}

function ResultPanel({ result, imageFile, drawnImage, onMessage }: ResultPanelProps) {
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

        // 绘制OCR结果文字（如果有坐标信息）
        const boxes = result.result?.[0] || []
        const recRes = result.result?.[1] || []

        if (boxes.length > 0) {
          ctx.strokeStyle = '#ff0000'
          ctx.lineWidth = 2
          ctx.fillStyle = '#000000'

          boxes.forEach((box: any, index: number) => {
            if (Array.isArray(box)) {
              ctx.beginPath()
              ctx.moveTo(box[0][0], box[0][1])
              for (let i = 1; i < box.length; i++) {
                ctx.lineTo(box[i][0], box[i][1])
              }
              ctx.closePath()
              ctx.stroke()

              // 在框内绘制文本
              const recResult = recRes[index]
              if (recResult && recResult[0]) {
                const text = recResult[0]
                // 计算框的中心位置来绘制文字
                const minX = Math.min(...box.map((c: number[]) => c[0]))
                const minY = Math.min(...box.map((c: number[]) => c[1]))
                const maxX = Math.max(...box.map((c: number[]) => c[0]))
                const maxY = Math.max(...box.map((c: number[]) => c[1]))
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
        contentToCopy = extractTextFromResult(result)
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
      content = extractTextFromResult(result)
      filename = 'ocr_result.txt'
      mimeType = 'text/plain'
    } else {
      // 下载JSON格式的结果
      content = JSON.stringify(result || {}, null, 2)
      filename = 'ocr_result.json'
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
            <option value="ocr-text">纯文本</option>
          </select>
        </div>
      </div>

      <div className="result-body">
        {result ? (
          view === 'json' ? (
            <pre>{JSON.stringify(result, null, 2)}</pre>
          ) : view === 'ocr-text' ? (
            <div className="ocr-text">
              <pre>{extractTextFromResult(result)}</pre>
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