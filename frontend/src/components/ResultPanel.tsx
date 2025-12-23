import { useState } from 'react'

interface ResultPanelProps {
  result: any
}

function ResultPanel({ result }: ResultPanelProps) {
  const [view, setView] = useState<'markdown' | 'json'>('json')

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
          <label htmlFor="view-select" className="sr-only">结果格式</label>
          <select
            id="view-select"
            className="view-select"
            value={view}
            onChange={(e) => setView(e.target.value as 'markdown' | 'json')}
          >
            <option value="markdown">Markdown</option>
            <option value="json">JSON</option>
          </select>
        </div>
      </div>

      <div className="result-body">
        <div className="result-actions-overlay">
          <button className="action-btn copy-btn" onClick={copyResult}>复制</button>
          <button className="action-btn download-btn" onClick={downloadResult}>下载</button>
        </div>
        {result ? (
          view === 'json' ? (
            <pre>{JSON.stringify(result, null, 2)}</pre>
          ) : (
            <div className="markdown">{/* 简单渲染，后续可用 markdown-it */}
              <pre>{result.text || JSON.stringify(result, null, 2)}</pre>
            </div>
          )
        ) : (
          <p>尚无解析结果</p>
        )}
      </div>
    </aside>
  )
}

export default ResultPanel