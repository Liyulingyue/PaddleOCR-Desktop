import { useState } from 'react'

interface ImageResultPanelProps {
  imageUrl: string | null
  imageFile?: File | null
  elapsedTime: number | null
  resultShape?: string
  onMessage?: (msg: string) => void
}

export default function ImageResultPanel({
  imageUrl,
  imageFile,
  elapsedTime,
  resultShape,
  onMessage
}: ImageResultPanelProps) {
  const [copied, setCopied] = useState(false)

  const handleDownload = () => {
    if (!imageUrl) return
    const a = document.createElement('a')
    a.href = imageUrl
    a.download = imageFile ? `result_${imageFile.name}` : 'result.png'
    a.click()
    onMessage?.('图片已下载')
  }

  const handleCopy = async () => {
    if (!imageUrl) return
    try {
      const resp = await fetch(imageUrl)
      const blob = await resp.blob()
      await navigator.clipboard.write([
        new ClipboardItem({ [blob.type]: blob })
      ])
      setCopied(true)
      onMessage?.('图片已复制到剪贴板')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      onMessage?.('复制失败，请尝试右键保存图片')
    }
  }

  return (
    <aside className="result-panel">
      <div className="result-panel-header">
        <h3>结果</h3>
        <div className="action-buttons">
          {imageUrl && (
            <>
              <button className="action-btn copy-btn" onClick={handleCopy} title="复制图片">
                {copied ? '✓ 已复制' : '📋 复制图片'}
              </button>
              <button className="action-btn download-btn" onClick={handleDownload} title="下载图片">
                💾 下载
              </button>
            </>
          )}
        </div>
      </div>

      <div className="result-body">
        {imageUrl ? (
          <>
            <div className="result-meta">
              {elapsedTime !== null && (
                <span className="timing-badge">
                  推理耗时: <strong>{elapsedTime.toFixed(3)}s</strong>
                </span>
              )}
              {resultShape && (
                <span className="shape-badge">尺寸: {resultShape}</span>
              )}
            </div>
            <div className="drawn-image">
              <img src={imageUrl} alt="结果" />
            </div>
          </>
        ) : (
          <div className="empty-state">
            <p>结果将显示在这里</p>
          </div>
        )}
      </div>
    </aside>
  )
}
