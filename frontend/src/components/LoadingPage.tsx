import { useEffect, useState } from 'react'
import '../styles/loading.css'

interface LoadingPageProps {
  onBackendReady: () => void
  maxWaitTime?: number
}

export const LoadingPage = ({ onBackendReady, maxWaitTime = 60000 }: LoadingPageProps) => {
  const [status, setStatus] = useState<'connecting' | 'checking' | 'ready' | 'timeout'>('connecting')
  const [elapsedTime, setElapsedTime] = useState(0)

  useEffect(() => {
    const checkBackendHealth = async () => {
      const startTime = Date.now()
      console.log('⏳ 等待服务启动...')

      const checkHealth = async (): Promise<boolean> => {
        setStatus('checking')

        try {
          // 只从 Tauri 获取后端URL，被动等待后端启动并输出 port
          if (typeof window !== 'undefined' && '__TAURI__' in window) {
            try {
              const { invoke } = await import('@tauri-apps/api/tauri')
              const backendUrl = await invoke<string>('get_backend_url')

              if (backendUrl && backendUrl !== 'http://localhost:8002') {
                const response = await fetch(`${backendUrl}/api/health`, {
                  method: 'GET',
                  signal: AbortSignal.timeout(2000)
                })

                if (response.ok) {
                  console.log(`✅ Backend is ready at ${backendUrl}`)
                  setStatus('ready')
                  return true
                }
              }
            } catch (err) {
              // 继续等待后端启动
            }
          }

          return false
        } catch (err) {
          return false
        }
      }

      // 定期检查后端健康状态
      const healthCheckInterval = setInterval(async () => {
        const elapsed = Date.now() - startTime
        setElapsedTime(Math.floor(elapsed / 1000))

        if (elapsed > maxWaitTime) {
          clearInterval(healthCheckInterval)
          setStatus('timeout')
          console.error(`❌ Backend health check timed out after ${maxWaitTime / 1000}s`)
          return
        }

        const isHealthy = await checkHealth()
        if (isHealthy) {
          clearInterval(healthCheckInterval)
          setStatus('ready')
          setTimeout(onBackendReady, 500) // 给UI更新的时间
        }
      }, 1000) // 每秒检查一次

      // 立即进行第一次检查
      const isHealthy = await checkHealth()
      if (isHealthy) {
        setStatus('ready')
        setTimeout(onBackendReady, 500)
      }
    }

    checkBackendHealth()
  }, [onBackendReady, maxWaitTime])

  return (
    <div className="loading-page">
      <div className="loading-container">
        <div className="loading-content">
          <div className="logo-container">
            <h1>PaddleOCR Desktop</h1>
          </div>

          <div className="spinner"></div>

          <div className="status-section">
            <h2>
              {status === 'connecting' && '等待服务启动...'}
              {status === 'checking' && '正在检查服务状态...'}
              {status === 'ready' && '✅ 服务已就绪'}
              {status === 'timeout' && '❌ 启动超时'}
            </h2>
            
            <div className="status-details">
              <p className="elapsed-time">
                {elapsedTime} 秒
              </p>
            </div>
          </div>

          {status === 'timeout' && (
            <div className="error-section">
              <p>后端服务启动失败，请检查日志并重新启动应用</p>
              <button 
                onClick={() => window.location.reload()}
                className="retry-btn"
              >
                重试
              </button>
            </div>
          )}

          <div className="tips">
            <p>🔄 正在启动后端服务，初次运行需要加载模型，请耐心等待...</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoadingPage
