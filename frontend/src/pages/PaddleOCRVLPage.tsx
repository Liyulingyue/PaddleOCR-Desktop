import { useState, useEffect, useRef } from 'react'
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
  const [llamaServerUrl, setLlamaServerUrl] = useState<string>('http://127.0.0.1:8080')
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
        } catch {}
      } catch {}
    }
    init()
  }, [])

  const checkServerConnection = async () => {
    if (!llamaServerUrl) return
    setCheckingServer(true)
    try {
      const resp = await fetch(`${llamaServerUrl}/v1/models`, { signal: AbortSignal.timeout(5000) })
      if (resp.ok) {
        setServerConnected(true)
        setMessageWithAutoClear('llama.cpp server connected successfully')
      } else {
        setServerConnected(false)
        setError('Server responded but may not be a valid llama.cpp server')
      }
    } catch (e: any) {
      setServerConnected(false)
      setError(`Cannot connect to llama.cpp server: ${e.message || 'timeout or network error'}`)
    } finally {
      setCheckingServer(false)
    }
  }

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setResult(null)
    setDrawnImage(null)
    setMarkdownContent(null)
    setMarkdownImages(null)
  }

  const handleClear = () => {
    setFile(null)
    setResult(null)
    setDrawnImage(null)
    setMarkdownContent(null)
    setMarkdownImages(null)
    setError(null)
  }

  const handleUpload = async () => {
    if (!file) return
    if (!llamaServerUrl) {
      setError('Please enter the llama.cpp server URL')
      return
    }
    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('llama_server_url', llamaServerUrl)
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
      } else {
        setError(data.error || 'Prediction failed')
      }
    } catch (e: any) {
      setError(`Network error: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="layout">
      {message && (
        <div className="global-message-banner">{message}</div>
      )}

      <div className="sidebar">
        <h2>PaddleOCR-VL 1.5</h2>

        <div className="control-section">
          <h3>llama.cpp Server</h3>
          <div className="input-group">
            <label>Server URL</label>
            <input
              type="text"
              value={llamaServerUrl}
              onChange={e => { setLlamaServerUrl(e.target.value); setServerConnected(false) }}
              placeholder="http://127.0.0.1:8080"
            />
          </div>
          <div className="input-group">
            <button
              className={`btn ${serverConnected ? 'btn-success' : 'btn-primary'}`}
              onClick={checkServerConnection}
              disabled={checkingServer || !llamaServerUrl}
            >
              {checkingServer ? 'Checking...' : serverConnected ? 'Connected' : 'Check Connection'}
            </button>
          </div>
          <p className="hint">
            Start llama-server: ./llama-server -m model.gguf --mmproj mmproj.gguf -fa -c 8192
          </p>
        </div>

        <div className="control-section">
          <h3>File</h3>
          <input
            type="file"
            accept="image/*,.pdf"
            onChange={e => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            className="file-input"
          />
          {file && <p className="file-name">{file.name}</p>}
        </div>

        <div className="control-section">
          <h3>Layout Detection</h3>
          <div className="input-group">
            <label>
              <input
                type="checkbox"
                checked={useLayoutDetection}
                onChange={e => setUseLayoutDetection(e.target.checked)}
              />
              Enable Layout Detection
            </label>
          </div>
          <div className="input-group">
            <label>Layout Model</label>
            <select value={layoutModel} onChange={e => setLayoutModel(e.target.value)}>
              <option value="Default">Default</option>
              <option value="PP-DocLayout-L-ONNX">PP-DocLayout-L-ONNX</option>
              <option value="PP-DocLayout-M-ONNX">PP-DocLayout-M-ONNX</option>
              <option value="PP-DocLayout-S-ONNX">PP-DocLayout-S-ONNX</option>
              <option value="PP-DocLayout_plus-L-ONNX">PP-DocLayout_plus-L-ONNX</option>
            </select>
          </div>
          <div className="input-group">
            <label>Confidence Threshold: {layoutConfThreshold.toFixed(2)}</label>
            <input
              type="range"
              min="0" max="1" step="0.05"
              value={layoutConfThreshold}
              onChange={e => setLayoutConfThreshold(parseFloat(e.target.value))}
            />
          </div>
          <div className="input-group">
            <label>
              <input
                type="checkbox"
                checked={mergeLayoutBlocks}
                onChange={e => setMergeLayoutBlocks(e.target.checked)}
              />
              Merge Layout Blocks
            </label>
          </div>
        </div>

        <div className="control-section">
          <h3>VLM Parameters</h3>
          <div className="input-group">
            <label>Max New Tokens: {maxNewTokens}</label>
            <input
              type="range"
              min="256" max="8192" step="256"
              value={maxNewTokens}
              onChange={e => setMaxNewTokens(parseInt(e.target.value))}
            />
          </div>
          <div className="input-group">
            <label>Temperature: {temperature.toFixed(2)}</label>
            <input
              type="range"
              min="0" max="2" step="0.05"
              value={temperature}
              onChange={e => setTemperature(parseFloat(e.target.value))}
            />
          </div>
          <div className="input-group">
            <label>Top-P{topP !== null ? `: ${topP.toFixed(2)}` : ''}</label>
            <input
              type="number"
              min="0" max="1" step="0.05"
              value={topP ?? ''}
              placeholder="Leave empty to disable"
              onChange={e => setTopP(e.target.value ? parseFloat(e.target.value) : null)}
            />
          </div>
          <div className="input-group">
            <label>Repetition Penalty{repetitionPenalty !== null ? `: ${repetitionPenalty.toFixed(2)}` : ''}</label>
            <input
              type="number"
              min="1" max="2" step="0.05"
              value={repetitionPenalty ?? ''}
              placeholder="Leave empty to disable"
              onChange={e => setRepetitionPenalty(e.target.value ? parseFloat(e.target.value) : null)}
            />
          </div>
          <div className="input-group">
            <label>Min Pixels{minPixels !== null ? `: ${minPixels}` : ''}</label>
            <input
              type="number"
              value={minPixels ?? ''}
              placeholder="Leave empty to use default"
              onChange={e => setMinPixels(e.target.value ? parseInt(e.target.value) : null)}
            />
          </div>
          <div className="input-group">
            <label>Max Pixels{maxPixels !== null ? `: ${maxPixels}` : ''}</label>
            <input
              type="number"
              value={maxPixels ?? ''}
              placeholder="Leave empty to use default"
              onChange={e => setMaxPixels(e.target.value ? parseInt(e.target.value) : null)}
            />
          </div>
        </div>

        <div className="button-group">
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={loading || !file}
          >
            {loading ? 'Processing...' : 'Analyze'}
          </button>
          <button className="btn btn-secondary" onClick={handleClear}>
            Clear
          </button>
        </div>

        {error && (
          <div className="error-banner">
            {error}
          </div>
        )}
      </div>

      <div className="main-content">
        {file && (
          <div className="viewer-container">
            <img
              src={URL.createObjectURL(file)}
              alt="Input"
              className="viewer-image"
            />
          </div>
        )}

        {result && (
          <div className="result-container">
            <div className="result-tabs">
              <div className="result-tab active">Results</div>
            </div>

            <div className="result-content">
              <div className="result-section">
                <h4>Layout Detection</h4>
                {result.layout_det_res?.boxes && (
                  <div className="result-boxes">
                    <p>Detected {result.layout_det_res.boxes.length} regions</p>
                    <div className="box-list">
                      {result.layout_det_res.boxes.slice(0, 20).map((box: any, i: number) => (
                        <div key={i} className="box-item">
                          <span className="box-label">{box.label}</span>
                          <span className="box-score">{(box.score * 100).toFixed(1)}%</span>
                        </div>
                      ))}
                      {result.layout_det_res.boxes.length > 20 && (
                        <p className="more">...and {result.layout_det_res.boxes.length - 20} more</p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {drawnImage && (
                <div className="result-section">
                  <h4>Visualization</h4>
                  <img src={drawnImage} alt="Visualization" className="result-image" />
                </div>
              )}

              <div className="result-section">
                <h4>Extracted Content</h4>
                <div className="content-list">
                  {result.parsing_res_list?.map((item: any, i: number) => (
                    <div key={i} className={`content-item content-item-${item.label || 'text'}`}>
                      <div className="content-header">
                        <span className="content-label">[{item.label}]</span>
                        {item.bbox && (
                          <span className="content-bbox">
                            ({item.bbox[0]}, {item.bbox[1]}, {item.bbox[2]}, {item.bbox[3]})
                          </span>
                        )}
                      </div>
                      <div className="content-text">
                        {item.content ? item.content.substring(0, 500) : '(no content)'}
                        {item.content && item.content.length > 500 && '...'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {markdownContent && (
                <div className="result-section">
                  <h4>Markdown Output</h4>
                  <div
                    className="markdown-preview"
                    dangerouslySetInnerHTML={{
                      __html: renderMarkdown(markdownContent, markdownImages || {})
                    }}
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function renderMarkdown(md: string, images: { [key: string]: string }): string {
  let html = md
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, src) => {
      if (images[src]) {
        return `<img src="${images[src]}" alt="${alt}" style="max-width:100%;" />`
      }
      return `<img src="${src}" alt="${alt}" style="max-width:100%;" />`
    })
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>')

  return `<p>${html}</p>`
}

export default PaddleOCRVLPage
