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

  if (!file) {
    return (
      <div className="viewer empty">
        <p>请选择或上传文件以开始识别</p>
      </div>
    )
  }

  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')

  return (
    <div className="viewer">
      <div className="viewer-header">
        <h3>原始文件</h3>
      </div>
      <div className="viewer-content">
        {isPdf ? (
          // For simplicity we embed the PDF; full page control would require pdf.js
          <embed src={`${url || ''}#page=${page}`} type="application/pdf" width="100%" height="100%" />
        ) : (
          <img src={url || ''} alt={file.name} />
        )}
      </div>
    </div>
  )
}

export default Viewer