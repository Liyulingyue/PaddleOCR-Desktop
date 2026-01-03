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
  pageType?: string
}

function ControlBar({ onFileSelect, file, loading, error, onUpload, onClear, config, onConfigChange, onShowApiModal, apiBaseUrl = '', onMessage, pageType = 'ocr' }: SidebarProps) {
  const [ocrConfigExpanded, setOcrConfigExpanded] = useState(false)
  const [ppstructureOcrConfigExpanded, setPpstructureOcrConfigExpanded] = useState(false)

  // Model status panel
  const [modelExpanded, setModelExpanded] = useState(false)
  const [modelLoaded, setModelLoaded] = useState<boolean | null>(null)
  const [modelActionLoading, setModelActionLoading] = useState(false)

  const showMsg = (m: string) => {
    if (onMessage) onMessage(m)
    else console.info(m)
  }

  const getApiPrefix = () => {
    return pageType === 'ppstructure' ? '/api/ppstructure' : '/api/ocr'
  }

  const fetchModelStatus = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}${getApiPrefix()}/model_status`)
      if (res.ok) {
        const j = await res.json()
        setModelLoaded(Boolean(j.loaded))
        return j.loaded
      } else {
        const t = await res.text()
        showMsg(`查询模型状态失败: ${res.status} ${t}`)
      }
    } catch (err) {
      showMsg('查询模型状态失败：网络错误')
    }
    setModelLoaded(null)
    return null
  }

  const loadModel = async () => {
    setModelActionLoading(true)
    try {
      const res = await fetch(`${apiBaseUrl}${getApiPrefix()}/load`, { method: 'POST' })
      if (res.ok) {
        showMsg('模型加载完成')
        setModelLoaded(true)
      } else {
        const t = await res.text()
        showMsg(`加载模型失败: ${res.status} ${t}`)
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

  // 自动在组件挂载时预加载当前状态
  useEffect(() => {
    fetchModelStatus()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <aside className="control-bar">
      <div className="control-bar-header">
        <h3>控制板</h3>
      </div>
      <FileUpload onFileSelect={onFileSelect} />

      <div className="control-section">
        <div className="button-group">
          <button onClick={onUpload} disabled={loading || !file} className="control-btn primary-btn">
            {loading ? '处理中...' : '开始识别'}
          </button>
          <button onClick={onClear} disabled={loading} className="control-btn secondary-btn">
            清空
          </button>
        </div>
        <div className="api-button-row">
          <button onClick={onShowApiModal} className="control-btn info-btn">
            📖 API文档
          </button>
        </div>
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

      <div className="control-section">
        <div 
          className="config-section-header"
          onClick={() => setOcrConfigExpanded(!ocrConfigExpanded)}
        >
          <h4>{pageType === 'ppstructure' ? '布局检测配置参数' : 'OCR配置参数'}</h4>
          <span className={`expand-icon ${ocrConfigExpanded ? 'expanded' : ''}`}>▼</span>
        </div>
        {ocrConfigExpanded && (
          <div className="config-content">
            {pageType === 'ppstructure' ? (
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
                  <label htmlFor="cls-threshold">方向检测阈值: {config.clsThresh}</label>
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
                  <small className="config-description">控制方向检测的置信度阈值，低于此值将跳过旋转</small>
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
                  <label htmlFor="cls-thresh">分类阈值: {config.clsThresh}</label>
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
                  <small className="config-description">控制文本方向分类的置信度阈值</small>
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

      {pageType === 'ppstructure' && (
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