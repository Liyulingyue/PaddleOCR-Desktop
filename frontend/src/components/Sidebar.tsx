import FileUpload from './FileUpload'

interface SidebarProps {
  onFileSelect: (file: File) => void
  file: File | null
  loading: boolean
  error: string | null
  onUpload: () => void
}

function Sidebar({ onFileSelect, file, loading, error, onUpload }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h3>控制板</h3>
      </div>
      <FileUpload onFileSelect={onFileSelect} />

      {file && (
        <div className="control-section">
          <button onClick={onUpload} disabled={loading} className="control-btn primary-btn">
            {loading ? '处理中...' : '开始识别'}
          </button>
          {error && <span className="error">{error}</span>}
        </div>
      )}
    </aside>
  )
}

export default Sidebar