import { useState, useEffect, useRef } from 'react'
import Viewer from '../components/Viewer'
import FileUpload from '../components/FileUpload'
import ResultPanel from '../components/ResultPanel'
import ErrorModal from '../components/ErrorModal'
import { getCachedApiBaseUrl } from '../utils/api'

interface VLPredictionResult {
  width?: number
  height?: number
  page_number?: number
  total_pages?: number
  layout_det_res?: { boxes: any[] }
  parsing_res_list?: Array<{
    label: string
    bbox: number[]
    content: string
    polygon_points?: number[][]
  }>
  pages?: VLPredictionResult[]
  file_type?: string
}

function PaddleOCRVLPage() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<VLPredictionResult | null>(null)
  const [drawnImage, setDrawnImage] = useState<string | null>(null)
  const [markdownContent, setMarkdownContent] = useState<string | null>(null)
  const [markdownImages, setMarkdownImages] = useState<{ [key: string]: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [apiBaseUrl, setApiBaseUrl] = useState<string>('')
  const [llamaManagerUrl, setLlamaManagerUrl] = useState<string>('http://127.0.0.1:8081')
  const [layoutModel, setLayoutModel] = useState<string>('Default')
  const [layoutConfThreshold, setLayoutConfThreshold] = useState<number>(0.5)
  const [useLayoutDetection, setUseLayoutDetection] = useState<boolean>(true)
  const [mergeLayoutBlocks, setMergeLayoutBlocks] = useState<boolean>(true)
  const [maxNewTokens, setMaxNewTokens] = useState<number>(4096)
  const [temperature, setTemperature] = useState<number>(0.0)
  const [topP, setTopP] = useState<number | null>(null)
  const [repetitionPenalty, setRepetitionPenalty] = useState<number | null>(null)
  const [minPixels, setMinPixels] = useState<number | null>(null)
  const [maxPixels, setMaxPixels] = useState<number | null>(null)
  const [serverConnected, setServerConnected] = useState<boolean>(false)
  const [checkingServer, setCheckingServer] = useState(false)
  const [showErrorModal, setShowErrorModal] = useState(false)
  const [errorModalData, setErrorModalData] = useState<{ title: string; message: string }>({ title: '', message: '' })
  const messageTimerRef = useRef<NodeJS.Timeout | null>(null)

  const setMessageWithAutoClear = (msg: string | null, duration = 5000) => {
    if (messageTimerRef.current) clearTimeout(messageTimerRef.current)
    setMessage(msg)
    if (msg) {
      messageTimerRef.current = setTimeout(() => setMessage(null), duration)
    }
  }

  useEffect(() => {
    return () => {
      if (messageTimerRef.current) clearTimeout(messageTimerRef.current)
    }
  }, [])

  useEffect(() => {
    const init = async () => {
      try {
        const url = await getCachedApiBaseUrl()
        setApiBaseUrl(url)
        try {
          const resp = await fetch(`${url}/api/ppocr_vl/options`)
          if (resp.ok) {
            const data = await resp.json()
            if (data.defaults?.layout_model) {
              setLayoutModel(data.defaults.layout_model)
            }
          }
        } catch { /* ignore */ }
      } catch { /* ignore */ }
    }
    init()
  }, [])

  const checkServerConnection = async () => {
    if (!llamaManagerUrl) return
    setCheckingServer(true)
    try {
      const resp = await fetch(`${llamaManagerUrl}/health`, { signal: AbortSignal.timeout(5000) })
      if (resp.ok) {
        setServerConnected(true)
        setMessageWithAutoClear('llama-manager is running')
      } else {
        setServerConnected(false)
        setError('llama-manager responded but may not be valid')
      }
    } catch (e: any) {
      setServerConnected(false)
      setError(`Cannot connect to llama-manager: ${e.message || 'timeout or network error'}`)
    } finally {
      setCheckingServer(false)
    }
  }

  const handleUpload = async () => {
    if (!file) return
    if (!llamaManagerUrl) {
      setError('Please enter the llama-manager URL')
      return
    }
    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('llama_manager_url', llamaManagerUrl)
    formData.append('layout_conf_threshold', layoutConfThreshold.toString())
    formData.append('use_layout_detection', useLayoutDetection.toString())
    formData.append('merge_layout_blocks', mergeLayoutBlocks.toString())
    formData.append('max_new_tokens', maxNewTokens.toString())
    formData.append('temperature', temperature.toString())
    if (topP !== null) formData.append('top_p', topP.toString())
    if (repetitionPenalty !== null) formData.append('repetition_penalty', repetitionPenalty.toString())
    if (minPixels !== null) formData.append('min_pixels', minPixels.toString())
    if (maxPixels !== null) formData.append('max_pixels', maxPixels.toString())
    if (layoutModel !== 'Default') formData.append('layout_model', layoutModel)

    try {
      const resp = await fetch(`${apiBaseUrl}/api/ppocr_vl/predict`, {
        method: 'POST',
        body: formData,
      })
      const data = await resp.json()
      if (resp.ok) {
        setResult(data)

        const drawFormData = new FormData()
        drawFormData.append('file', file)
        drawFormData.append('analysis_result', JSON.stringify(data))
        const drawResp = await fetch(`${apiBaseUrl}/api/ppocr_vl/draw`, {
          method: 'POST',
          body: drawFormData,
        })
        if (drawResp.ok) {
          const contentType = drawResp.headers.get('content-type')
          if (contentType?.includes('image')) {
            const blob = await drawResp.blob()
            const imageUrl = URL.createObjectURL(blob)
            setDrawnImage(imageUrl)
          }
        }

        const mdFormData = new FormData()
        mdFormData.append('file', file)
        mdFormData.append('analysis_result', JSON.stringify(data))
        const mdResp = await fetch(`${apiBaseUrl}/api/ppocr_vl/markdown`, {
          method: 'POST',
          body: mdFormData,
        })
        if (mdResp.ok) {
          const mdData = await mdResp.json()
          const imgs: { [key: string]: string } = {}
          if (mdData.images && Array.isArray(mdData.images)) {
            mdData.images.forEach((img: any) => {
              if (img.filename && img.data) {
                imgs[img.filename] = `data:image/png;base64,${img.data}`
              }
            })
          }
          setMarkdownContent(mdData.markdown || '')
          setMarkdownImages(imgs)
        }
      } else {
        if (data.missingFiles) {
          setErrorModalData({
            title: '模型文件缺失',
            message: data.error || '模型文件不完整，请下载缺失的模型文件',
          })
        } else {
          setError(data.error || 'Prediction failed')
        }
      }
    } catch (e: any) {
      setError(`Network error: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setFile(null)
    setResult(null)
    setDrawnImage(null)
    setMarkdownContent(null)
    setMarkdownImages(null)
    setError(null)
  }

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setResult(null)
    setDrawnImage(null)
    setMarkdownContent(null)
    setMarkdownImages(null)
  }

  return (
    <div className="layout">
      {message && (
        <div className="global-message-banner">{message}</div>
      )}

      <aside className="control-bar">
        <div className="control-bar-header">
          <h3>PaddleOCR-VL 1.5</h3>
        </div>

        <FileUpload onFileSelect={handleFileSelect} />

        <div className="control-section">
          <div className="button-group">
            <button onClick={handleUpload} disabled={loading || !file} className="control-btn primary-btn">
              {loading ? 'Processing...' : 'Analyze'}
            </button>
            <button onClick={handleClear} disabled={loading} className="control-btn secondary-btn">
              Clear
            </button>
          </div>
          {error && <span className="error">{error}</span>}
        </div>

        <div className="control-section">
          <div className="config-section-header">
            llama-manager
            <span className="expand-icon">▼</span>
          </div>
          <div className="config-content">
            <div className="config-item">
              <label>Manager URL</label>
              <input
                type="text"
                value={llamaManagerUrl}
                onChange={e => { setLlamaManagerUrl(e.target.value); setServerConnected(false) }}
                placeholder="http://127.0.0.1:8081"
                className="config-input"
              />
            </div>
            <div className="config-item">
              <button
                onClick={checkServerConnection}
                disabled={checkingServer || !llamaManagerUrl}
                className={`control-btn small ${serverConnected ? 'primary-btn' : 'secondary-btn'}`}
              >
                {checkingServer ? 'Checking...' : serverConnected ? 'Connected' : 'Check Connection'}
              </button>
            </div>
          </div>
        </div>

        <div className="control-section">
          <div className="config-section-header">
            Layout Detection
            <span className="expand-icon">▼</span>
          </div>
          <div className="config-content">
            <div className="config-item">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={useLayoutDetection}
                  onChange={e => setUseLayoutDetection(e.target.checked)}
                />
                Enable Layout Detection
              </label>
            </div>
            <div className="config-item">
              <label className="checkbox-label">
                Merge Layout Blocks
              </label>
              <input
                type="checkbox"
                checked={mergeLayoutBlocks}
                onChange={e => setMergeLayoutBlocks(e.target.checked)}
              />
            </div>
            <div className="config-item">
              <label>Confidence: {layoutConfThreshold.toFixed(2)}</label>
              <div className="range-labels">
                <input
                  type="range" min="0" max="1" step="0.05"
                  value={layoutConfThreshold}
                  onChange={e => setLayoutConfThreshold(parseFloat(e.target.value))}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="control-section">
          <div className="config-section-header">
            VLM Parameters
            <span className="expand-icon">▼</span>
          </div>
          <div className="config-content">
            <div className="config-item">
              <label>Max Tokens: {maxNewTokens}</label>
              <div className="range-labels">
                <input type="range" min="256" max="8192" step="256" value={maxNewTokens}
                  onChange={e => setMaxNewTokens(parseInt(e.target.value))} />
              </div>
            </div>
            <div className="config-item">
              <label>Temperature: {temperature.toFixed(2)}</label>
              <div className="range-labels">
                <input type="range" min="0" max="2" step="0.05" value={temperature}
                  onChange={e => setTemperature(parseFloat(e.target.value))} />
              </div>
            </div>
            <div className="config-item">
              <label>Top-P</label>
              <input type="number" min="0" max="1" step="0.05" value={topP ?? ''}
                placeholder="default"
                onChange={e => setTopP(e.target.value ? parseFloat(e.target.value) : null)}
                className="config-input" />
            </div>
            <div className="config-item">
              <label>Repetition Penalty</label>
              <input type="number" min="1" max="2" step="0.05" value={repetitionPenalty ?? ''}
                placeholder="default"
                onChange={e => setRepetitionPenalty(e.target.value ? parseFloat(e.target.value) : null)}
                className="config-input" />
            </div>
            <div className="config-item">
              <label>Min Pixels</label>
              <input type="number" value={minPixels ?? ''} placeholder="default"
                onChange={e => setMinPixels(e.target.value ? parseInt(e.target.value) : null)}
                className="config-input" />
            </div>
            <div className="config-item">
              <label>Max Pixels</label>
              <input type="number" value={maxPixels ?? ''} placeholder="default"
                onChange={e => setMaxPixels(e.target.value ? parseInt(e.target.value) : null)}
                className="config-input" />
            </div>
          </div>
        </div>
      </aside>

      <Viewer file={file} />

      <ResultPanel
        result={result}
        imageFile={file}
        drawnImage={drawnImage}
        onMessage={setMessageWithAutoClear}
        resultType="layout"
        viewOptions={['json', 'drawn-image', 'markdown']}
        markdownContent={markdownContent}
        markdownImages={markdownImages}
      />

      <ErrorModal
        isOpen={showErrorModal}
        onClose={() => setShowErrorModal(false)}
        title={errorModalData?.title || ''}
        message={errorModalData?.message || ''}
      />
    </div>
  )
}

export default PaddleOCRVLPage
