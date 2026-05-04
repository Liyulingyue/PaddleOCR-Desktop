import { useState, useEffect, useRef } from 'react'
import ControlBar from '../components/ControlBar'
import Viewer from '../components/Viewer'
import ErrorModal from '../components/ErrorModal'
import ApiModal from '../components/ApiModal'
import { getCachedApiBaseUrl } from '../utils/api'
import './FormulaPage.css'

function FormulaPage() {
  const [file, setFile] = useState<File | null>(null)
  const [latex, setLatex] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [apiBaseUrl, setApiBaseUrl] = useState<string>('')
  const [showErrorModal, setShowErrorModal] = useState(false)
  const [errorModalData, setErrorModalData] = useState<{title: string, message: string, missingFiles?: string[]} | null>(null)
  const [showApiModal, setShowApiModal] = useState(false)
  const [elapsedTime, setElapsedTime] = useState<number | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [config, setConfig] = useState<Record<string, any>>({})
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
    setLatex(null)
    setElapsedTime(null)
  }

  const handleClear = () => {
    setFile(null)
    setLatex(null)
    setError(null)
    setElapsedTime(null)
  }

  const handleCopy = async () => {
    if (!latex) return
    try {
      await navigator.clipboard.writeText(latex)
      setCopied(true)
      setMessageWithAutoClear('已复制到剪贴板')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setMessageWithAutoClear('复制失败')
    }
  }

  const handleRecognize = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setLatex(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('model', config.formulaModel || 'PP-FormulaNet_plus-M-ONNX')
      const res = await fetch(`${apiBaseUrl}/api/formula/recognize`, {
        method: 'POST',
        body: formData
      })

      if (!res.ok) {
        const data = await res.json()
        setErrorModalData({ title: '⚠️ 公式识别失败', message: data.error })
        setShowErrorModal(true)
        return
      }

      const data = await res.json()
      setLatex(data.latex)
      setElapsedTime(data.elapsed)
      setMessageWithAutoClear('识别完成！')
    } catch {
      setError('网络错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`layout ${latex ? '' : 'no-result'}`}>
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
        onUpload={handleRecognize}
        onClear={handleClear}
        config={config}
        onConfigChange={setConfig}
        onShowApiModal={() => setShowApiModal(true)}
        apiBaseUrl={apiBaseUrl}
        onMessage={setMessageWithAutoClear}
        onShowErrorModal={(data: {title: string, message: string, missingFiles?: string[]}) => {
          setErrorModalData(data)
          setShowErrorModal(true)
        }}
        pageType="formula"
      />

      <Viewer file={file} />

      <aside className="result-panel">
        <div className="result-panel-header">
          <h3>识别结果</h3>
          <div className="action-buttons">
            {latex && (
              <button className="action-btn copy-btn" onClick={handleCopy} title="复制">
                {copied ? '✓ 已复制' : '📋 复制'}
              </button>
            )}
          </div>
        </div>

        <div className="result-body">
          {latex ? (
            <>
              <div className="result-meta">
                {elapsedTime !== null && (
                  <span className="timing-badge">
                    推理耗时: <strong>{elapsedTime.toFixed(3)}s</strong>
                  </span>
                )}
              </div>
              <div className="formula-latex-box">
                <div className="formula-latex-label">LaTeX</div>
                <pre className="formula-latex-text">{latex}</pre>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <p>上传公式图像，点击「开始识别」获取 LaTeX</p>
            </div>
          )}
        </div>
      </aside>

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
        type="formula"
      />
    </div>
  )
}

export default FormulaPage
