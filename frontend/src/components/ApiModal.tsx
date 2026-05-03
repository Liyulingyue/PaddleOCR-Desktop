import React, { useRef } from 'react'
import { ocrApiData, ppStructureApiData, uvdocApiData, type ApiEndpoint } from '../utils/apiData'

interface ApiModalProps {
  isOpen: boolean
  onClose: () => void
  apiBaseUrl: string
  type: 'ocr' | 'ppstructure' | 'uvdoc'
}

const ApiModal: React.FC<ApiModalProps> = ({ isOpen, onClose, apiBaseUrl, type }) => {
  const scrollRef = useRef<HTMLDivElement>(null)

  if (!isOpen) return null

  const data = type === 'ocr' ? ocrApiData : type === 'ppstructure' ? ppStructureApiData : uvdocApiData

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id)
    if (element && scrollRef.current) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const renderEndpoint = (endpoint: ApiEndpoint) => (
    <div key={endpoint.id} id={endpoint.id} className="api-endpoint-detail">
      <div className="api-endpoint-header">
        <h4>{endpoint.title}</h4>
        <div className="api-endpoint-badge">
          <span className={`method-badge ${endpoint.method.toLowerCase()}`}>{endpoint.method}</span>
          <span className="path-text">{endpoint.path}</span>
        </div>
      </div>
      
      <p className="endpoint-desc">{endpoint.description}</p>

      {endpoint.params && (
        <div className="params-section">
          <h5>请求参数：</h5>
          <table className="params-table">
            <thead>
              <tr>
                <th>参数名</th>
                <th>说明</th>
                <th>类型</th>
                <th>默认值</th>
              </tr>
            </thead>
            <tbody>
              {endpoint.params.map(p => (
                <tr key={p.name}>
                  <td><code>{p.name}</code></td>
                  <td>{p.description}</td>
                  <td>{p.type || '-'}</td>
                  <td>{p.default || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {endpoint.additionalInfo && (() => {
        const pdfItems = endpoint.additionalInfo.filter(i => /pdf/i.test(i));
        const otherItems = endpoint.additionalInfo.filter(i => !/pdf/i.test(i));
        return (
          <>
            {pdfItems.length > 0 && (
              <div className="pdf-info-section">
                <h5>PDF文件处理说明：</h5>
                <ul>{pdfItems.map((info, i) => <li key={i}>{info}</li>)}</ul>
              </div>
            )}
            {otherItems.length > 0 && (
              <div className="info-section">
                <h5>功能说明：</h5>
                <ul>{otherItems.map((info, i) => <li key={i}>{info}</li>)}</ul>
              </div>
            )}
          </>
        );
      })()}

      <div className="examples-section">
        <h5>代码示例：</h5>
        <div className="examples-tabs">
          {endpoint.examples.map((ex, i) => (
            <div key={i} className="example-item">
              <h6>{ex.lang}</h6>
              <pre className="code-block">
                <code>{ex.code(apiBaseUrl)}</code>
              </pre>
            </div>
          ))}
        </div>
      </div>

      {endpoint.response && (
        <div className="response-section">
          <h5>{endpoint.responseTitle || '返回格式'}：</h5>
          <pre className="response-block">
            <code>{endpoint.response}</code>
          </pre>
        </div>
      )}
    </div>
  )

  return (
    <div className="api-modal-overlay" onClick={onClose}>
      <div className="api-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="api-modal-sidebar">
          <div className="sidebar-header">
            <h3>导航</h3>
          </div>
          <div className="sidebar-nav">
            <div className="sidebar-item" onClick={() => scrollToSection('base-url')}>
              🔗 接口地址
            </div>
            {data.map(category => (
              <div key={category.id} className="nav-group">
                <div className="nav-group-title">{category.title}</div>
                {category.endpoints.map(ep => (
                  <div 
                    key={ep.id} 
                    className="sidebar-item endpoint-link"
                    onClick={() => scrollToSection(ep.id)}
                  >
                    {ep.title}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>

        <div className="api-modal-main">
          <div className="api-modal-header">
            <h3>API 文档 - {type === 'ocr' ? 'OCR 识别' : type === 'ppstructure' ? 'PP-Structure' : '文档纠偏'}</h3>
            <button className="close-btn" onClick={onClose}>×</button>
          </div>
          
          <div className="api-modal-content" ref={scrollRef}>
            <div id="base-url" className="api-section base-url-section">
              <h4>🔗 接口基准地址</h4>
              <div className="api-url-wrapper">
                <code className="api-url">{apiBaseUrl}</code>
              </div>
              <p className="api-note">API路径会自动转发到后端服务器</p>
            </div>

            {data.map(category => (
              <div key={category.id} className="api-category-section">
                <h3 className="category-title">{category.title}</h3>
                {category.endpoints.map(renderEndpoint)}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ApiModal
