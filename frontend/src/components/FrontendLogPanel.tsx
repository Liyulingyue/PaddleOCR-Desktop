import { useEffect, useState } from 'react'

export function FrontendLogPanel() {
  const [visible, setVisible] = useState(false)
  const [logs, setLogs] = useState<string>('')

  useEffect(() => {
    // 重写 console.log 来收集日志
    const originalLog = console.log
    const originalError = console.error
    const originalWarn = console.warn
    const originalInfo = console.info

    const addLog = (level: string, ...args: any[]) => {
      const message = `[${new Date().toLocaleTimeString()}] ${level}: ${args.join(' ')}`
      setLogs(prev => prev + '\n' + message)
    }

    console.log = (...args) => {
      originalLog(...args)
      addLog('LOG', ...args)
    }

    console.error = (...args) => {
      originalError(...args)
      addLog('ERROR', ...args)
    }

    console.warn = (...args) => {
      originalWarn(...args)
      addLog('WARN', ...args)
    }

    console.info = (...args) => {
      originalInfo(...args)
      addLog('INFO', ...args)
    }

    // 清理函数
    return () => {
      console.log = originalLog
      console.error = originalError
      console.warn = originalWarn
      console.info = originalInfo
    }
  }, [])

  const clearLogs = () => {
    setLogs('')
  }

  return (
    <div style={{ position: 'fixed', right: 12, bottom: 60, zIndex: 1000 }}>
      <button onClick={() => setVisible(v => !v)} style={{ padding: '6px 10px' }}>
        {visible ? 'Hide Frontend Logs' : 'Show Frontend Logs'}
      </button>

      {visible && (
        <div style={{ width: 640, height: 360, marginTop: 8, background: '#fff', border: '1px solid #ddd', padding: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.12)', overflow: 'auto' }}>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 12 }}>{logs || 'No frontend logs yet'}</pre>
          <div style={{ marginTop: 8, textAlign: 'right' }}>
            <button onClick={clearLogs}>Clear</button>
          </div>
        </div>
      )}
    </div>
  )
}