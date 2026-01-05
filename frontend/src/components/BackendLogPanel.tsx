import { useEffect, useState } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import { listen } from '@tauri-apps/api/event'

export function BackendLogPanel() {
  const [visible, setVisible] = useState(false)
  const [logs, setLogs] = useState<string>('')

  useEffect(() => {
    // 订阅实时事件
    let unlisten: (() => void) | undefined
    listen<string>('backend-log', (event) => {
      setLogs((s) => s + '\n' + event.payload)
    }).then((u) => (unlisten = u))

    return () => {
      if (unlisten) unlisten()
    }
  }, [])

  const fetchLogs = async () => {
    try {
      const result: string = await invoke('read_backend_logs')
      setLogs(result)
    } catch (e) {
      setLogs('Failed to read logs: ' + String(e))
    }
  }

  const clearLogs = async () => {
    try {
      await invoke('clear_backend_logs')
      setLogs('')
    } catch (e) {
      console.error('Failed to clear logs:', e)
      // 即使后端清空失败，也清空前端显示
      setLogs('')
    }
  }

  return (
    <div style={{ position: 'fixed', right: 12, bottom: 12, zIndex: 1000 }}>
      <button onClick={() => { setVisible((v) => !v); if (!visible) fetchLogs() }} style={{ padding: '6px 10px' }}>
        {visible ? 'Hide Logs' : 'Show Backend Logs'}
      </button>

      {visible && (
        <div style={{ width: 640, height: 360, marginTop: 8, background: '#fff', border: '1px solid #ddd', padding: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.12)', overflow: 'auto' }}>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 12 }}>{logs || 'No logs yet'}</pre>
          <div style={{ marginTop: 8, textAlign: 'right' }}>
            <button onClick={() => fetchLogs()} style={{ marginRight: 8 }}>Refresh</button>
            <button onClick={() => clearLogs()} style={{ backgroundColor: '#ff6b6b', color: 'white' }}>Clear</button>
          </div>
        </div>
      )}
    </div>
  )
}
