import { useState, useRef, useEffect } from 'react'

interface ResultPanelProps {
  result: any
  imageFile: File | null
  drawnImage: string | null
}

function ResultPanel({ result, imageFile, drawnImage }: ResultPanelProps) {
  const [view, setView] = useState<'ocr-text' | 'markdown' | 'json' | 'drawn-image'>('ocr-text')
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
      await navigator.clipboard.writeText(JSON.stringify(result || {}, null, 2))
      alert('已复制')
    } catch (e) {
      alert('复制失败')
    }
  }

  const downloadResult = () => {
    const blob = new Blob([JSON.stringify(result || {}, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'result.json'
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
            onChange={(e) => setView(e.target.value as 'ocr-text' | 'markdown' | 'json' | 'drawn-image')}
          >
            <option value="ocr-text">OCR识别</option>
            <option value="markdown">Markdown</option>
            <option value="json">JSON</option>
            <option value="drawn-image">绘制图像</option>
          </select>
        </div>
      </div>

      <div className="result-body">
        {result ? (
          view === 'json' ? (
            <pre>{JSON.stringify(result, null, 2)}</pre>
          ) : view === 'markdown' ? (
            <div className="markdown">{/* 简单渲染，后续可用 markdown-it */}
              <pre>{result.text || JSON.stringify(result, null, 2)}</pre>
            </div>
          ) : view === 'drawn-image' ? (
            <div className="drawn-image">
              {drawnImage ? (
                <img src={drawnImage} alt="OCR结果绘制" style={{ maxWidth: '100%', height: 'auto' }} />
              ) : (
                <p>绘制图像加载中...</p>
              )}
            </div>
          ) : (
            <div className="ocr-text">
              {imageFile ? (
                <canvas 
                  ref={canvasRef} 
                  style={{ maxWidth: '100%', height: 'auto' }}
                />
              ) : (
                <pre>{result.text || '暂无识别结果'}</pre>
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