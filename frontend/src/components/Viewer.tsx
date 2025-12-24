import { useEffect, useState } from 'react'

interface ViewerProps {
  file: File | null
  page: number
  onPageChange: (page: number) => void
}

function Viewer({ file, page, onPageChange }: ViewerProps) {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setUrl(null)
      return
    }
    const u = URL.createObjectURL(file)
    setUrl(u)
    return () => {
      URL.revokeObjectURL(u)
    }
  }, [file])

  const isPdf = file && (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'))
  const isImage = file && (file.type.startsWith('image/') || /\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(file.name))

  return (
    <div className="viewer">
      <div className="viewer-toolbar">
        <h3>原始文件</h3>
        <div className="viewer-controls">
          {isPdf && (
            <div className="page-controls">
              <button
                className="nav-btn"
                onClick={() => onPageChange(Math.max(1, page - 1))}
                disabled={page <= 1}
                title="上一页"
              >
                ‹
              </button>
              <span className="page-number" title={`第 ${page} 页`}>{page}</span>
              <button
                className="nav-btn"
                onClick={() => onPageChange(page + 1)}
                title="下一页"
              >
                ›
              </button>
            </div>
          )}
          {isImage && (
            <div className="page-info">
              <span className="page-indicator">单页图片</span>
            </div>
          )}
        </div>
      </div>
      <div className="viewer-content">
        {file ? (
          isPdf ? (
            url ? (
              // For simplicity we embed the PDF; full page control would require pdf.js
              <embed src={`${url}#page=${page}`} type="application/pdf" width="100%" height="100%" />
            ) : (
              <div className="loading">加载中...</div>
            )
          ) : url ? (
            <img src={url} alt={file.name} />
          ) : (
            <div className="loading">加载中...</div>
          )
        ) : (
          <div className="empty-state">
            <p>请选择或上传文件以开始识别</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Viewer