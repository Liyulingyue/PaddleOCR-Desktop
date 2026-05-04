import { useState, useEffect } from 'react'
import FileUpload from './FileUpload'

interface SidebarProps {
  onFileSelect: (file: File) => void
  file: File | null
  loading: boolean
  error: string | null
  onUpload: () => void
  onClear: () => void
  config: any
  onConfigChange: (config: any) => void
  onShowApiModal: () => void
  apiBaseUrl?: string
  onMessage?: (msg: string) => void
  onShowErrorModal?: (data: {title: string, message: string, missingFiles?: string[]}) => void
  pageType?: string
}

function ControlBar({ onFileSelect, file, loading, error, onUpload, onClear, config, onConfigChange, onShowApiModal, apiBaseUrl = '', onMessage, onShowErrorModal, pageType = 'ocr' }: SidebarProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const pt: any = pageType ?? 'ocr'
  const [ocrConfigExpanded, setOcrConfigExpanded] = useState(false)
  const [ppstructureOcrConfigExpanded, setPpstructureOcrConfigExpanded] = useState(false)
  const [modelSelectionExpanded, setModelSelectionExpanded] = useState(false)

  // Model status panel
  const [modelExpanded, setModelExpanded] = useState(false)

  // Model options from backend
  const [modelOptions, setModelOptions] = useState<{
    det: Array<{value: string, label: string, description: string}>,
    rec: Array<{value: string, label: string, description: string}>,
    cls: Array<{value: string, label: string, description: string}>,
    textlineCls?: Array<{value: string, label: string, description: string}>,
    layout?: Array<{value: string, label: string, description: string}>
  } | null>(null)
  const [loadingModelOptions, setLoadingModelOptions] = useState(false)
  const [modelLoaded, setModelLoaded] = useState<boolean | null>(null)
  const [modelActionLoading, setModelActionLoading] = useState(false)
  const [useGpu, setUseGpu] = useState(false)
  const [checkingModels, setCheckingModels] = useState(false)
  const [checkStatus, setCheckStatus] = useState<string | null>(null)

  const showMsg = (m: string) => {
    if (onMessage) onMessage(m)
    else console.info(m)
  }

  const getApiPrefix = () => {
    if (pt === 'ppstructure') return '/api/ppstructure'
    if (pt === 'uvdoc') return '/api/uvdoc/unwarp'
    if (pt === 'formula') return '/api/formula/recognize'
    return '/api/ocr'
  }

  const fetchModelStatus = async () => {
    try {
      const url = `${apiBaseUrl}${getApiPrefix()}/model_status`
      console.log('Fetching model status from:', url)
      const res = await fetch(url)
      console.log('Model status response:', res.status, res.ok)
      if (res.ok) {
        const j = await res.json()
        console.log('Model status data:', j)
        setModelLoaded(Boolean(j.loaded))
        if (j.use_gpu !== undefined) {
          setUseGpu(j.use_gpu)
        }
        return j.loaded
      } else {
        const t = await res.text()
        console.log('Model status error response:', t)
        showMsg(`查询模型状态失败: ${res.status} ${t}`)
      }
    } catch (err) {
      console.log('Model status fetch error:', err)
      showMsg('查询模型状态失败：网络错误')
    }
    setModelLoaded(null)
    return null
  }

  const loadModel = async () => {
    setModelActionLoading(true)
    try {
      const formData = new FormData()
      formData.append('use_gpu', useGpu.toString())
      const res = await fetch(`${apiBaseUrl}${getApiPrefix()}/load`, { method: 'POST', body: formData })
      if (res.ok) {
        showMsg(useGpu ? '模型加载完成 (GPU)' : '模型加载完成 (CPU)')
        setModelLoaded(true)
      } else {
        const t = await res.text()
        let errorMessage = `加载模型失败: ${res.status} ${t}`
        showMsg(errorMessage)
        
        // 检查是否为模型文件缺失错误
        try {
          const errorData = JSON.parse(t)
          if (errorData.error && (errorData.error.includes('模型文件不完整') || errorData.error.includes('模型文件缺失'))) {
            if (onShowErrorModal) {
              const missingFiles = errorData.missing_files || []
              onShowErrorModal({
                title: '⚠️ 模型文件缺失',
                message: '模型加载失败，检测到模型文件缺失，请前往模型管理页面下载所需的模型。',
                missingFiles: missingFiles
              })
            }
          }
        } catch (parseErr) {
          // 如果不是JSON，忽略
        }
      }
    } catch (err) {
      showMsg('加载模型失败：网络错误')
    } finally {
      setModelActionLoading(false)
    }
  }

  const unloadModel = async () => {
    setModelActionLoading(true)
    try {
      const res = await fetch(`${apiBaseUrl}${getApiPrefix()}/unload`, { method: 'POST' })
      if (res.ok) {
        showMsg('模型已卸载')
        setModelLoaded(false)
      } else {
        const t = await res.text()
        showMsg(`卸载模型失败: ${res.status} ${t}`)
      }
    } catch (err) {
      showMsg('卸载模型失败：网络错误')
    } finally {
      setModelActionLoading(false)
    }
  }

  // 初次展开时查询一次状态
  const handleModelToggle = async () => {
    const next = !modelExpanded
    setModelExpanded(next)
    if (next && modelLoaded === null) {
      await fetchModelStatus()
    }
  }

  const handleCheckAndDownloadModels = async () => {
    setCheckingModels(true)
    setCheckStatus(null)
    try {
      const apiPrefix = getApiPrefix()
      
      // 首先检查模型状态
      const statusRes = await fetch(`${apiBaseUrl}${apiPrefix}/model_status`)
      if (statusRes.ok) {
        const statusData = await statusRes.json()
        if (statusData.loaded) {
          setCheckStatus('✅ 所有模型文件已完整')
          setTimeout(() => setCheckStatus(null), 3000)
          return
        }
      }

      // 如果模型未加载，调用下载接口（只下载，不加载到内存）
      setCheckStatus('⏳ 正在下载缺失模型...')
      const downloadRes = await fetch(`${apiBaseUrl}${apiPrefix}/download_missing`, {
        method: 'POST'
      })
      
      if (downloadRes.ok) {
        await downloadRes.json()
        setCheckStatus('✅ 模型下载完成！')
        setTimeout(() => setCheckStatus(null), 3000)
      } else {
        const errorData = await downloadRes.json()
        const errorMsg = errorData.error || '模型下载失败'
        setCheckStatus(`❌ ${errorMsg}`)
      }
    } catch (error) {
      setCheckStatus(`❌ 下载失败：${error instanceof Error ? error.message : '未知错误'}`)
    } finally {
      setCheckingModels(false)
    }
  }

  // 自动在组件挂载时预加载当前状态
  useEffect(() => {
    if (apiBaseUrl) {
      fetchModelStatus()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBaseUrl])

  // 获取模型选项
  useEffect(() => {
    const fetchModelOptions = async () => {
      if (!apiBaseUrl) return

      setLoadingModelOptions(true)
      try {
        let response;
        if (pt === 'ppstructure') {
          response = await fetch(`${apiBaseUrl}/api/ppstructure/options`)
        } else if (pt === 'ocr') {
          response = await fetch(`${apiBaseUrl}/api/ocr/options`)
        } else if (pt === 'formula') {
          response = await fetch(`${apiBaseUrl}/api/formula/recognize/model_options`)
          if (response.ok) {
            const data = await response.json()
            setModelOptions({ formula: data.options || [] })
            return
          }
        } else {
          return
        }
        
        if (response.ok) {
          const data = await response.json()
          // 映射后端返回的组件名称到前端期望的名称
          let mappedOptions;
          if (pt === 'ppstructure') {
            mappedOptions = {
              layout: data.options.layout_det || [],
              det: data.options.ocr_det || [],
              rec: data.options.ocr_rec || [],
              cls: data.options.doc_cls || [],
              textlineCls: data.options.textline_cls || []
            }
          } else {
            mappedOptions = {
              det: data.options.ocr_det || [],
              rec: data.options.ocr_rec || [],
              cls: data.options.doc_cls || [],
              textlineCls: data.options.textline_cls || []
            }
          }
          
          // 添加"Default"选项到每个模型类型
          const optionsWithDefault = {
            ...mappedOptions,
            layout: pt === 'ppstructure' ? [
              { value: 'Default', label: '默认模型', description: '使用系统默认的布局检测模型' },
              ...mappedOptions.layout
            ] : undefined,
            det: [
              { value: 'Default', label: '默认模型', description: '使用系统默认的检测模型' },
              ...mappedOptions.det
            ],
            rec: [
              { value: 'Default', label: '默认模型', description: '使用系统默认的识别模型' },
              ...mappedOptions.rec
            ],
            cls: [
              { value: 'Default', label: '默认模型', description: '使用系统默认的方向检测模型' },
              ...mappedOptions.cls
            ],
            textlineCls: mappedOptions.textlineCls ? [
              { value: 'Default', label: '默认模型', description: '使用系统默认的文本行方向检测模型' },
              ...mappedOptions.textlineCls
            ] : undefined
          }
          setModelOptions(optionsWithDefault)
        } else {
          console.error('Failed to fetch model options:', response.status)
        }
      } catch (error) {
        console.error('Error fetching model options:', error)
      } finally {
        setLoadingModelOptions(false)
      }
    }

    fetchModelOptions()
  }, [apiBaseUrl, pageType])

  return (
    <aside className="control-bar">
      <div className="control-bar-header">
        <h3>控制板</h3>
      </div>
      <FileUpload onFileSelect={onFileSelect} />

      <div className="control-section">
        <div className="button-group">
          <button onClick={onUpload} disabled={loading || !file} className="control-btn primary-btn">
            {loading ? (pt === 'uvdoc' ? '纠偏中...' : pt === 'formula' ? '识别中...' : '处理中...') : (pt === 'uvdoc' ? '开始纠偏' : pt === 'formula' ? '开始识别' : '开始识别')}
          </button>
          <button onClick={onClear} disabled={loading} className="control-btn secondary-btn">
            清空
          </button>
        </div>
        <div className="api-button-row">
          <button onClick={onShowApiModal} className="control-btn info-btn">
            📖 API文档
          </button>
          <button
            onClick={handleCheckAndDownloadModels}
            disabled={checkingModels}
            className="control-btn info-btn"
            style={{ marginLeft: '0.5rem' }}
          >
            {checkingModels ? '⏳ 下载中...' : '📥 下载缺失模型'}
          </button>
        </div>
        {checkStatus && (
          <div className="check-status" style={{ 
            marginTop: '0.5rem', 
            padding: '0.5rem',
            borderRadius: '4px',
            fontSize: '0.85rem',
            backgroundColor: checkStatus.includes('✅') ? '#d4edda' : checkStatus.includes('❌') ? '#f8d7da' : '#e2e3e5',
            color: checkStatus.includes('✅') ? '#155724' : checkStatus.includes('❌') ? '#721c24' : '#383d41'
          }}>
            {checkStatus}
          </div>
        )}
        {error && <span className="error">{error}</span>}
      </div>

      <div className="control-section">
        <div 
          className="config-section-header"
          onClick={() => handleModelToggle()}
        >
          <h4>模型加载状态</h4>
          <span className={`expand-icon ${modelExpanded ? 'expanded' : ''}`}>▼</span>
        </div>
        {modelExpanded && (
          <div className="config-content">
            <div className="config-item model-status">
              <div className="model-status-row">
                <div className="model-status-left">
                  <label>当前状态：</label>
                  <span className={modelLoaded ? 'status-loaded' : modelLoaded === false ? 'status-unloaded' : 'status-unknown'}>
                    {modelLoaded === true ? '已加载' : modelLoaded === false ? '未加载' : '未知'}
                  </span>
                </div>
                <div className="model-status-right">
                  <button className="control-btn small refresh-btn" onClick={() => fetchModelStatus()}>刷新</button>
                </div>
              </div>

              <div className="config-item">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={useGpu}
                    onChange={(e) => setUseGpu(e.target.checked)}
                    disabled={modelActionLoading || modelLoaded === true}
                  />
                  使用GPU加速
                </label>
                <small className="config-description">启用GPU推理（需重新加载模型）</small>
              </div>

              <div className="model-controls row">
                <button onClick={loadModel} disabled={modelActionLoading || modelLoaded === true} className="control-btn primary-btn">
                  {modelActionLoading ? '处理中...' : '加载模型'}
                </button>
                <button onClick={unloadModel} disabled={modelActionLoading || modelLoaded === false} className="control-btn secondary-btn">
                  卸载模型
                </button>
              </div>
            </div>
          </div>
        )}

      </div>

      {pt !== 'uvdoc' && pt !== 'formula' && (
      <div className="control-section">
        <div
          className="config-section-header"
          onClick={() => setOcrConfigExpanded(!ocrConfigExpanded)}
        >
          <h4>预处理配置</h4>
          <span className={`expand-icon ${ocrConfigExpanded ? 'expanded' : ''}`}>▼</span>
        </div>
        {ocrConfigExpanded && (
          <div className="config-content">
            <div className="config-item">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={config.useUVDoc}
                  onChange={(e) => onConfigChange({ ...config, useUVDoc: e.target.checked })}
                  disabled={loading}
                />
                启用文档纠偏 (UVDoc)
              </label>
              <small className="config-description">纠正弯曲/透视变形的文档图像，在方向检测前执行</small>
            </div>
            {pt === 'ppstructure' && (
            <div className="config-item">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={config.useFormulaRec ?? true}
                  onChange={(e) => onConfigChange({ ...config, useFormulaRec: e.target.checked })}
                  disabled={loading}
                />
                启用公式识别 (PP-FormulaNet)
              </label>
              <small className="config-description">识别文档中的数学公式并输出 LaTeX 文本</small>
            </div>
            )}
          </div>
        )}
      </div>
      )}

      {pt !== 'uvdoc' && pt !== 'formula' && (
      <div className="control-section">
        <div
          className="config-section-header"
          onClick={() => setOcrConfigExpanded(!ocrConfigExpanded)}
        >
          <h4>{pt === 'ppstructure' ? '布局检测配置参数' : 'OCR配置参数'}</h4>
          <span className={`expand-icon ${ocrConfigExpanded ? 'expanded' : ''}`}>▼</span>
        </div>
        {ocrConfigExpanded && (
          <div className="config-content">
            {pt === 'ppstructure' ? (
              <>
                <div className="config-item">
                  <label htmlFor="conf-threshold">布局检测阈值: {config.confThreshold}</label>
                  <input
                    id="conf-threshold"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.confThreshold}
                    onChange={(e) => onConfigChange({ ...config, confThreshold: parseFloat(e.target.value) })}
                    disabled={loading}
                  />
                  <div className="range-labels">
                    <span>0.0</span>
                    <span>1.0</span>
                  </div>
                  <small className="config-description">控制布局检测的置信度阈值</small>
                </div>

                <div className="config-item">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={config.useCls}
                      onChange={(e) => onConfigChange({ ...config, useCls: e.target.checked })}
                      disabled={loading}
                    />
                    启用方向检测
                  </label>
                  <small className="config-description">自动检测和纠正文档方向（0°、90°、180°、270°）</small>
                </div>

                <div className="config-item">
                  <label htmlFor="cls-threshold">文档方向阈值: {config.clsThresh}</label>
                  <input
                    id="cls-threshold"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.clsThresh}
                    onChange={(e) => onConfigChange({ ...config, clsThresh: parseFloat(e.target.value) })}
                    disabled={loading || !config.useCls}
                  />
                  <div className="range-labels">
                    <span>0.0</span>
                    <span>1.0</span>
                  </div>
                  <small className="config-description">控制文档方向检测的置信度阈值</small>
                </div>

                <div className="config-item">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={config.useTextlineCls}
                      onChange={(e) => onConfigChange({ ...config, useTextlineCls: e.target.checked })}
                      disabled={loading}
                    />
                    启用文本行方向检测
                  </label>
                  <small className="config-description">检测单个文本行是否倒置(180度)，自动翻转后再识别</small>
                </div>

                <div className="config-item">
                  <label htmlFor="textline-cls-thresh-pp">文本行方向阈值: {config.textlineClsThresh}</label>
                  <input
                    id="textline-cls-thresh-pp"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.textlineClsThresh}
                    onChange={(e) => onConfigChange({ ...config, textlineClsThresh: parseFloat(e.target.value) })}
                    disabled={loading || !config.useTextlineCls}
                  />
                  <div className="range-labels">
                    <span>0.0</span>
                    <span>1.0</span>
                  </div>
                  <small className="config-description">控制文本行方向检测的置信度阈值</small>
                </div>

                <div className="config-item">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={config.mergeLayout}
                      onChange={(e) => onConfigChange({ ...config, mergeLayout: e.target.checked })}
                      disabled={loading}
                    />
                    合并重叠布局框
                  </label>
                  <small className="config-description">启用基于重叠度的布局框合并（仅同类型框会合并）</small>
                </div>

                <div className="config-item">
                  <label htmlFor="layout-overlap-threshold">布局重叠度阈值: {config.layoutOverlapThreshold}</label>
                  <input
                    id="layout-overlap-threshold"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.layoutOverlapThreshold}
                    onChange={(e) => onConfigChange({ ...config, layoutOverlapThreshold: parseFloat(e.target.value) })}
                    disabled={loading || !config.mergeLayout}
                  />
                  <div className="range-labels">
                    <span>0.0</span>
                    <span>1.0</span>
                  </div>
                  <small className="config-description">控制布局框合并的重叠度阈值（交集/最小面积），较高值只合并高度重叠的框</small>
                </div>
              </>
            ) : (
              <>
                <div className="config-item">
                  <label htmlFor="det-thresh">检测阈值: {config.detThresh}</label>
                  <input
                    id="det-thresh"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.detThresh}
                    onChange={(e) => onConfigChange({ ...config, detThresh: parseFloat(e.target.value) })}
                    disabled={loading}
                  />
                  <div className="range-labels">
                    <span>0.0</span>
                    <span>1.0</span>
                  </div>
                  <small className="config-description">控制文本检测的灵敏度，较低值检测更多文本</small>
                </div>

                <div className="config-item">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={config.useCls}
                      onChange={(e) => onConfigChange({ ...config, useCls: e.target.checked })}
                      disabled={loading}
                    />
                    启用文本方向分类
                  </label>
                  <small className="config-description">是否执行文本方向检测和矫正</small>
                </div>

                <div className="config-item">
                  <label htmlFor="cls-thresh">文档方向阈值: {config.clsThresh}</label>
                  <input
                    id="cls-thresh"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.clsThresh}
                    onChange={(e) => onConfigChange({ ...config, clsThresh: parseFloat(e.target.value) })}
                    disabled={loading || !config.useCls}
                  />
                  <div className="range-labels">
                    <span>0.0</span>
                    <span>1.0</span>
                  </div>
                  <small className="config-description">控制文档方向分类的置信度阈值</small>
                </div>

                <div className="config-item">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={config.useTextlineCls}
                      onChange={(e) => onConfigChange({ ...config, useTextlineCls: e.target.checked })}
                      disabled={loading}
                    />
                    启用文本行方向检测
                  </label>
                  <small className="config-description">检测单个文本行是否倒置(180度)，自动翻转后再识别</small>
                </div>

                <div className="config-item">
                  <label htmlFor="textline-cls-thresh">文本行方向阈值: {config.textlineClsThresh}</label>
                  <input
                    id="textline-cls-thresh"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.textlineClsThresh}
                    onChange={(e) => onConfigChange({ ...config, textlineClsThresh: parseFloat(e.target.value) })}
                    disabled={loading || !config.useTextlineCls}
                  />
                  <div className="range-labels">
                    <span>0.0</span>
                    <span>1.0</span>
                  </div>
                  <small className="config-description">控制文本行方向检测的置信度阈值</small>
                </div>

                <div className="config-item">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={config.mergeOverlaps}
                      onChange={(e) => onConfigChange({ ...config, mergeOverlaps: e.target.checked })}
                      disabled={loading}
                    />
                    合并重叠检测框
                  </label>
                  <small className="config-description">启用基于重叠度阈值的重叠文本框合并功能</small>
                </div>

                <div className="config-item">
                  <label htmlFor="overlap-threshold-ocr">重叠度阈值: {config.overlapThreshold}</label>
                  <input
                    id="overlap-threshold-ocr"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={config.overlapThreshold}
                    onChange={(e) => onConfigChange({ ...config, overlapThreshold: parseFloat(e.target.value) })}
                    disabled={loading || !config.mergeOverlaps}
                  />
                  <div className="range-labels">
                    <span>0.0</span>
                    <span>1.0</span>
                  </div>
                  <small className="config-description">控制重叠框合并的重叠度阈值（交集/最小面积），较高值只合并高度重叠的框</small>
                </div>
              </>
            )}
          </div>
        )}
      </div>
      )}

      {(pt === 'ocr' || pt === 'formula') && (
        <div className="control-section">
          <div
            className="config-section-header"
            onClick={() => setModelSelectionExpanded(!modelSelectionExpanded)}
          >
            <h4>{pt === 'formula' ? '公式模型' : '模型选择'}</h4>
            <span className={`expand-icon ${modelSelectionExpanded ? 'expanded' : ''}`}>▼</span>
          </div>
          {modelSelectionExpanded && (
            <div className="config-content">
              {loadingModelOptions ? (
                <div className="config-item">
                  <p>正在加载模型选项...</p>
                </div>
              ) : modelOptions ? (
                <>
                  {pt === 'ppstructure' && modelOptions?.layout && (
                    <div className="config-item">
                      <label htmlFor="layout-model">布局检测模型:</label>
                      <select
                        id="layout-model"
                        value={config.layoutModel || modelOptions.layout[0]?.value}
                        onChange={(e) => onConfigChange({ ...config, layoutModel: e.target.value })}
                        disabled={loading}
                        className="model-select"
                      >
                        {modelOptions.layout.map(option => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <small className="config-description">
                        {modelOptions.layout?.find(opt => opt.value === (config.layoutModel || modelOptions.layout?.[0]?.value))?.description || '选择用于文档布局检测的模型'}
                      </small>
                    </div>
                  )}

                  {pt !== 'formula' && (
                  <>
                  <div className="config-item">
                    <label htmlFor="det-model">{pt === 'ppstructure' ? 'OCR检测模型:' : '检测模型:'}</label>
                    <select
                      id="det-model"
                      value={config.detModel || modelOptions.det[0]?.value}
                      onChange={(e) => onConfigChange({ ...config, detModel: e.target.value })}
                      disabled={loading}
                      className="model-select"
                    >
                      {modelOptions.det.map(option => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <small className="config-description">
                      {modelOptions.det.find(opt => opt.value === (config.detModel || modelOptions.det[0]?.value))?.description || '选择用于文本检测的模型'}
                    </small>
                  </div>

                  <div className="config-item">
                    <label htmlFor="rec-model">{pt === 'ppstructure' ? 'OCR识别模型:' : '识别模型:'}</label>
                    <select
                      id="rec-model"
                      value={config.recModel || modelOptions.rec[0]?.value}
                      onChange={(e) => onConfigChange({ ...config, recModel: e.target.value })}
                      disabled={loading}
                      className="model-select"
                    >
                      {modelOptions.rec.map(option => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <small className="config-description">
                      {modelOptions.rec.find(opt => opt.value === (config.recModel || modelOptions.rec[0]?.value))?.description || '选择用于文本识别的模型'}
                    </small>
                  </div>

                  <div className="config-item">
                    <label htmlFor="cls-model">文档方向模型:</label>
                    <select
                      id="cls-model"
                      value={config.clsModel || modelOptions.cls[0]?.value}
                      onChange={(e) => onConfigChange({ ...config, clsModel: e.target.value })}
                      disabled={loading}
                      className="model-select"
                    >
                      {modelOptions.cls.map(option => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <small className="config-description">
                      {modelOptions.cls.find(opt => opt.value === (config.clsModel || modelOptions.cls[0]?.value))?.description || '选择用于文档方向检测的模型'}
                    </small>
                  </div>

                  {modelOptions.textlineCls && (
                  <div className="config-item">
                    <label htmlFor="textline-cls-model">文本行方向模型:</label>
                    <select
                      id="textline-cls-model"
                      value={config.textlineClsModel || modelOptions.textlineCls[0]?.value}
                      onChange={(e) => onConfigChange({ ...config, textlineClsModel: e.target.value })}
                      disabled={loading}
                      className="model-select"
                    >
                      {modelOptions.textlineCls.map(option => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <small className="config-description">
                      {modelOptions.textlineCls?.find(opt => opt.value === (config.textlineClsModel || modelOptions.textlineCls?.[0]?.value))?.description || '选择用于文本行方向检测的模型'}
                    </small>
                  </div>
                  )}
                  </>
                  )}

                  {pt === 'formula' && modelOptions.formula && (
                  <div className="config-item">
                    <label htmlFor="formula-model">公式识别模型:</label>
                    <select
                      id="formula-model"
                      value={config.formulaModel || modelOptions.formula[0]?.value}
                      onChange={(e) => onConfigChange({ ...config, formulaModel: e.target.value })}
                      disabled={loading}
                      className="model-select"
                    >
                      {modelOptions.formula.map(option => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <small className="config-description">
                      {modelOptions.formula.find(opt => opt.value === (config.formulaModel || modelOptions.formula[0]?.value))?.description || '选择公式识别模型'}
                    </small>
                  </div>
                  )}
                </>
              ) : (
                <div className="config-item">
                  <p>无法加载模型选项</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {pt === 'ppstructure' && (
        <div className="control-section">
          <div 
            className="config-section-header"
            onClick={() => setPpstructureOcrConfigExpanded(!ppstructureOcrConfigExpanded)}
          >
            <h4>OCR配置参数</h4>
            <span className={`expand-icon ${ppstructureOcrConfigExpanded ? 'expanded' : ''}`}>▼</span>
          </div>
          {ppstructureOcrConfigExpanded && (
            <div className="config-content">
              <div className="config-item">
                <label htmlFor="ocr-det-thresh">OCR检测阈值: {config.ocrDetThresh}</label>
                <input
                  id="ocr-det-thresh"
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={config.ocrDetThresh}
                  onChange={(e) => onConfigChange({ ...config, ocrDetThresh: parseFloat(e.target.value) })}
                  disabled={loading}
                />
                <div className="range-labels">
                  <span>0.0</span>
                  <span>1.0</span>
                </div>
                <small className="config-description">控制OCR文本检测的灵敏度，较低值检测更多文本</small>
              </div>
              <div className="config-item">
                <label htmlFor="unclip-ratio">裁剪扩大倍数: {config.unclipRatio}</label>
                <input
                  id="unclip-ratio"
                  type="range"
                  min="1.0"
                  max="2.0"
                  step="0.1"
                  value={config.unclipRatio}
                  onChange={(e) => onConfigChange({ ...config, unclipRatio: parseFloat(e.target.value) })}
                  disabled={loading}
                />
                <div className="range-labels">
                  <span>1.0</span>
                  <span>2.0</span>
                </div>
                <small className="config-description">扩大裁剪区域以包含完整文本，类似PaddleOCR的unclip算法，默认1.1倍</small>
              </div>

              <div className="config-item">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={config.mergeOverlaps}
                    onChange={(e) => onConfigChange({ ...config, mergeOverlaps: e.target.checked })}
                    disabled={loading}
                  />
                  合并重叠检测框
                </label>
                <small className="config-description">启用基于重叠度阈值的重叠文本框合并功能</small>
              </div>

              <div className="config-item">
                <label htmlFor="overlap-threshold">重叠度阈值: {config.overlapThreshold}</label>
                <input
                  id="overlap-threshold"
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={config.overlapThreshold}
                  onChange={(e) => onConfigChange({ ...config, overlapThreshold: parseFloat(e.target.value) })}
                  disabled={loading || !config.mergeOverlaps}
                />
                <div className="range-labels">
                  <span>0.0</span>
                  <span>1.0</span>
                </div>
                <small className="config-description">控制重叠框合并的重叠度阈值（交集/最小面积），较高值只合并高度重叠的框</small>
              </div>
            </div>
          )}
        </div>
      )}

    </aside>
  )
}

export default ControlBar