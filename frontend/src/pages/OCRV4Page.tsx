import { useState } from 'react'
import ControlBar from '../components/ControlBar'
import Viewer from '../components/Viewer'
import ResultPanel from '../components/ResultPanel'

function OCRV4Page() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<any>(null)
  const [drawnImage, setDrawnImage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setResult(null)
    setDrawnImage(null)
    setPage(1)
  }

  const handleClear = () => {
    setFile(null)
    setResult(null)
    setDrawnImage(null)
    setError(null)
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
      // Fetch OCR result
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

      // Fetch drawn image
      const drawResponse = await fetch('http://localhost:8000/api/ocr/draw', {
        method: 'POST',
        body: new FormData([['file', file]]), // Create new FormData for draw
      })
      if (drawResponse.ok) {
        const blob = await drawResponse.blob()
        const imageUrl = URL.createObjectURL(blob)
        setDrawnImage(imageUrl)
      } else {
        console.error('Failed to fetch drawn image')
      }
    } catch (err) {
      setError('网络错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="layout">
      <ControlBar
        onFileSelect={handleFileSelect}
        file={file}
        loading={loading}
        error={error}
        onUpload={handleUpload}
        onClear={handleClear}
      />
      <Viewer file={file} page={page} onPageChange={handlePageChange} />
      <ResultPanel result={result} imageFile={file} drawnImage={drawnImage} />
    </div>
  )
}

export default OCRV4Page
