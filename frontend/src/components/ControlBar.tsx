import { useState } from 'react'
import FileUpload from './FileUpload'

interface SidebarProps {
  onFileSelect: (file: File) => void
  file: File | null
  loading: boolean
  error: string | null
  onUpload: () => void
  onClear: () => void
  config: { 
    dropScore: number
    detThresh: number
    clsThresh: number
    useCls: boolean
  }
  onConfigChange: (config: { 
    dropScore: number
    detThresh: number
    clsThresh: number
    useCls: boolean
  }) => void
  onShowApiModal: () => void
}

function ControlBar({ onFileSelect, file, loading, error, onUpload, onClear, config, onConfigChange, onShowApiModal }: SidebarProps) {
  const [ocrConfigExpanded, setOcrConfigExpanded] = useState(false)
  const [drawConfigExpanded, setDrawConfigExpanded] = useState(false)
  return (
    <aside className="control-bar">
      <div className="control-bar-header">
        <h3>控制板</h3>
      </div>
      <FileUpload onFileSelect={onFileSelect} />

      <div className="control-section">
        <div 
          className="config-section-header"
          onClick={() => setOcrConfigExpanded(!ocrConfigExpanded)}
        >
          <h4>OCR配置参数</h4>
          <span className={`expand-icon ${ocrConfigExpanded ? 'expanded' : ''}`}>▼</span>
        </div>
        {ocrConfigExpanded && (
          <div className="config-content">
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
                  checked={config.useCls}
                  onChange={(e) => onConfigChange({ ...config, useCls: e.target.checked })}
                  disabled={loading}
                />
                启用文本方向分类
              </label>
              <small className="config-description">是否执行文本方向检测和矫正</small>
            </div>
          </div>
        )}
      </div>

      <div className="control-section">
        <div 
          className="config-section-header"
          onClick={() => setDrawConfigExpanded(!drawConfigExpanded)}
        >
          <h4>绘制配置参数</h4>
          <span className={`expand-icon ${drawConfigExpanded ? 'expanded' : ''}`}>▼</span>
        </div>
        {drawConfigExpanded && (
          <div className="config-content">
            <div className="config-item">
              <label htmlFor="drop-score">绘制阈值: {config.dropScore}</label>
              <input
                id="drop-score"
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={config.dropScore}
                onChange={(e) => onConfigChange({ ...config, dropScore: parseFloat(e.target.value) })}
                disabled={loading}
              />
              <div className="range-labels">
                <span>0.0</span>
                <span>1.0</span>
              </div>
              <small className="config-description">控制绘制时显示的识别结果最低置信度</small>
            </div>
          </div>
        )}
      </div>

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
    </aside>
  )
}

export default ControlBar