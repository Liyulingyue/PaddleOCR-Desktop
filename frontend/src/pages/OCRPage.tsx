import { useState } from 'react'
import Sidebar from '../components/Sidebar'
import Viewer from '../components/Viewer'
import ResultPanel from '../components/ResultPanel'

function OCRPage() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setResult(null)
    setPage(1)
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://localhost:8000/api/ocr', {
        method: 'POST',
        body: formData,
      })
      const data = await response.json()
      if (response.ok) {
        setResult(data.result)
      } else {
        setError(data.error || '上传失败')
      }
    } catch (err) {
      setError('网络错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="layout">
      <Sidebar
        onFileSelect={handleFileSelect}
        file={file}
        loading={loading}
        error={error}
        onUpload={handleUpload}
      />

      <Viewer file={file} page={page} onPageChange={handlePageChange} />
      <ResultPanel result={result} imageFile={file} />
    </div>
  )
}

export default OCRPage