import { useEffect, useState } from 'react'

interface ViewerProps {
  file: File | null
}

function Viewer({ file }: ViewerProps) {
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
            <div className="file-info">
              <span className="file-type">PDF文档</span>
            </div>
          )}
          {isImage && (
            <div className="file-info">
              <span className="file-type">图片文件</span>
            </div>
          )}
        </div>
      </div>
      <div className="viewer-content">
        {file ? (
          isPdf ? (
            url ? (
              <embed src={url} type="application/pdf" width="100%" height="100%" />
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