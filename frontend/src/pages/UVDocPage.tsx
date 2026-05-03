import { useState, useEffect, useRef } from 'react'
import ControlBar from '../components/ControlBar'
import Viewer from '../components/Viewer'
import ImageResultPanel from '../components/ImageResultPanel'
import ErrorModal from '../components/ErrorModal'
import ApiModal from '../components/ApiModal'
import { getCachedApiBaseUrl } from '../utils/api'
import './UVDocPage.css'

function UVDocPage() {
  const [file, setFile] = useState<File | null>(null)
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [apiBaseUrl, setApiBaseUrl] = useState<string>('')
  const [showErrorModal, setShowErrorModal] = useState(false)
  const [errorModalData, setErrorModalData] = useState<{title: string, message: string, missingFiles?: string[]} | null>(null)
  const [showApiModal, setShowApiModal] = useState(false)
  const [elapsedTime, setElapsedTime] = useState<number | null>(null)
  const [resultShape, setResultShape] = useState<string>('')
  const [message, setMessage] = useState<string | null>(null)
  const messageTimerRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    getCachedApiBaseUrl().then(setApiBaseUrl)
  }, [])

  const setMessageWithAutoClear = (newMessage: string | null, duration: number = 5000) => {
    if (messageTimerRef.current) clearTimeout(messageTimerRef.current)
    setMessage(newMessage)
    if (newMessage) {
      messageTimerRef.current = setTimeout(() => {
        setMessage(null)
        messageTimerRef.current = null
      }, duration)
    }
  }

  useEffect(() => {
    return () => {
      if (messageTimerRef.current) clearTimeout(messageTimerRef.current)
    }
  }, [])

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setResultUrl(null)
    setElapsedTime(null)
    setResultShape('')
  }

  const handleClear = () => {
    setFile(null)
    setResultUrl(null)
    setError(null)
    setElapsedTime(null)
    setResultShape('')
  }

  const handleUnwarp = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setResultUrl(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch(`${apiBaseUrl}/api/uvdoc/unwarp`, { method: 'POST', body: formData })

      if (!res.ok) {
        const data = await res.json()
        setErrorModalData({ title: '⚠️ 纠偏失败', message: data.error })
        setShowErrorModal(true)
        return
      }

      const elapsed = res.headers.get('X-Elapsed-Time')
      const resShape = res.headers.get('X-Result-Shape')
      if (elapsed) setElapsedTime(parseFloat(elapsed))
      if (resShape) setResultShape(resShape)

      const blob = await res.blob()
      setResultUrl(URL.createObjectURL(blob))
      setMessageWithAutoClear('纠偏完成！')
    } catch {
      setError('网络错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`layout ${resultUrl ? '' : 'no-result'}`}>
      {message && (
        <div className="global-message-banner">
          {message}
        </div>
      )}

      <ControlBar
        onFileSelect={handleFileSelect}
        file={file}
        loading={loading}
        error={error}
        onUpload={handleUnwarp}
        onClear={handleClear}
        config={{}}
        onConfigChange={() => {}}
        onShowApiModal={() => setShowApiModal(true)}
        apiBaseUrl={apiBaseUrl}
        onMessage={setMessageWithAutoClear}
        onShowErrorModal={(data: {title: string, message: string, missingFiles?: string[]}) => {
          setErrorModalData(data)
          setShowErrorModal(true)
        }}
        pageType="uvdoc"
      />

      <Viewer file={file} />

      <ImageResultPanel
        imageUrl={resultUrl}
        imageFile={file}
        elapsedTime={elapsedTime}
        resultShape={resultShape}
        onMessage={setMessageWithAutoClear}
      />

      <ErrorModal
        isOpen={showErrorModal}
        onClose={() => setShowErrorModal(false)}
        title={errorModalData?.title || ''}
        message={errorModalData?.message || ''}
        missingFiles={errorModalData?.missingFiles}
      />

      <ApiModal
        isOpen={showApiModal}
        onClose={() => setShowApiModal(false)}
        apiBaseUrl={apiBaseUrl}
        type="uvdoc"
      />
    </div>
  )
}

export default UVDocPage
