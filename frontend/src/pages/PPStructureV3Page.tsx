import { useState, useEffect, useRef } from 'react'
import ControlBar from '../components/ControlBar'
import Viewer from '../components/Viewer'
import ResultPanel from '../components/ResultPanel'
import { getCachedApiBaseUrl } from '../utils/api'

function PPStructureV3Page() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<any>(null)
  const [drawnImage, setDrawnImage] = useState<string | null>(null)
  const [markdownContent, setMarkdownContent] = useState<string | null>(null)
  const [markdownImageData, setMarkdownImageData] = useState<string | null>(null)
  const [markdownImages, setMarkdownImages] = useState<{ [key: string]: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState({
    confThreshold: 0.5,
    ocrDetThresh: 0.3,
    unclipRatio: 1.1,
    mergeOverlaps: false,
    overlapThreshold: 0.9,
    mergeLayout: false,
    layoutOverlapThreshold: 0.9,
    useCls: true,
    clsThresh: 0.9
  })
  const [message, setMessage] = useState<string | null>(null)
  const [showApiModal, setShowApiModal] = useState(false)
  const [apiBaseUrl, setApiBaseUrl] = useState<string>('')

  // 用于管理消息自动清除的定时器
  const messageTimerRef = useRef<NodeJS.Timeout | null>(null)

  // 设置消息并自动清除的函数
  const setMessageWithAutoClear = (newMessage: string | null, duration: number = 5000) => {
    // 清除之前的定时器
    if (messageTimerRef.current) {
      clearTimeout(messageTimerRef.current)
    }
    
    setMessage(newMessage)
    
    // 如果有新消息，设置定时器自动清除
    if (newMessage) {
      messageTimerRef.current = setTimeout(() => {
        setMessage(null)
        messageTimerRef.current = null
      }, duration)
    }
  }

  // 组件卸载时清除定时器
  useEffect(() => {
    return () => {
      if (messageTimerRef.current) {
        clearTimeout(messageTimerRef.current)
      }
    }
  }, [])

  // 获取API基础URL
  useEffect(() => {
    const fetchApiUrl = async () => {
      try {
        const url = await getCachedApiBaseUrl()
        setApiBaseUrl(url)
      } catch (error) {
        console.error('Failed to get API URL:', error)
      }
    }
    fetchApiUrl()
  }, [])

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile)
    setResult(null)
    setDrawnImage(null)
  }

  const handleConfigChange = (newConfig: { confThreshold: number; ocrDetThresh: number; unclipRatio: number; mergeOverlaps: boolean; overlapThreshold: number; mergeLayout: boolean; layoutOverlapThreshold: number; useCls: boolean; clsThresh: number }) => {
    setConfig(newConfig)
  }

  const handleClear = () => {
    setFile(null)
    setResult(null)
    setDrawnImage(null)
    setMarkdownContent(null)
    setMarkdownImageData(null)
    setError(null)
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('layout_conf_threshold', config.confThreshold.toString())
    formData.append('ocr_det_db_thresh', config.ocrDetThresh.toString())
    formData.append('unclip_ratio', config.unclipRatio.toString())
    formData.append('merge_overlaps', config.mergeOverlaps.toString())
    formData.append('overlap_threshold', config.overlapThreshold.toString())
    formData.append('merge_layout', config.mergeLayout.toString())
    formData.append('layout_overlap_threshold', config.layoutOverlapThreshold.toString())
    formData.append('use_cls', config.useCls.toString())
    formData.append('cls_thresh', config.clsThresh.toString())

    try {
      // Fetch layout detection result
      const response = await fetch('/api/ppstructure', {
        method: 'POST',
        body: formData,
      })
      const analysisResult = await response.json()
      if (response.ok) {
        // 处理多页PDF结果或单页结果
        let layoutRegions: any[] = []
        if (analysisResult.file_type === 'pdf' && analysisResult.pages) {
          // 多页PDF：汇总所有页面的layout_regions，并添加页码信息
          analysisResult.pages.forEach((page: any, pageIndex: number) => {
            if (page.layout_regions && Array.isArray(page.layout_regions)) {
              // 为每个layout_region添加页码信息
              const regionsWithPageInfo = page.layout_regions.map((region: any) => ({
                ...region,
                page_number: pageIndex + 1  // 页码从1开始
              }))
              layoutRegions = layoutRegions.concat(regionsWithPageInfo)
            }
          })
        } else {
          // 单页结果，添加页码信息
          const singlePageRegions = (analysisResult.layout_regions || []).map((region: any) => ({
            ...region,
            page_number: 1
          }))
          layoutRegions = singlePageRegions
        }
        setResult(layoutRegions)
      } else {
        setError(analysisResult.error || '上传失败')
      }

      // Fetch markdown content
      const markdownFormData = new FormData()
      markdownFormData.append('file', file)
      markdownFormData.append('analysis_result', JSON.stringify(analysisResult))
      const markdownResponse = await fetch('/api/ppstructure/markdown', {
        method: 'POST',
        body: markdownFormData,
      })
      if (markdownResponse.ok) {
        const markdownData = await markdownResponse.json()
        console.log('Markdown data received:', markdownData)
        console.log('Markdown content length:', markdownData.markdown?.length)
        console.log('Images count:', markdownData.images?.length)
        console.log('Sample images:', markdownData.images?.slice(0, 3))
        
        // 将图片数据转换为前端可用的格式
        const processedImages: { [key: string]: string } = {}
        if (markdownData.images && Array.isArray(markdownData.images)) {
          markdownData.images.forEach((img: any, index: number) => {
            console.log(`Processing image ${index}:`, { filename: img.filename, hasData: !!img.data, dataLength: img.data?.length })
            if (img.filename && img.data) {
              // 后端已经返回base64编码的数据，直接使用
              processedImages[img.filename] = `data:image/png;base64,${img.data}`
            }
          })
        }
        
        console.log('Processed images keys:', Object.keys(processedImages))
        setMarkdownContent(markdownData.markdown)
        setMarkdownImages(processedImages)
        console.log('Markdown content set with images:', Object.keys(processedImages))
      } else {
        console.error('Failed to fetch markdown content')
        setMarkdownContent('# Error\n\nFailed to generate markdown content.')
        setMarkdownImageData(null)
      }

      // Fetch drawn image
      const drawFormData = new FormData()
      drawFormData.append('file', file)
      drawFormData.append('analysis_result', JSON.stringify(analysisResult))
      const drawResponse = await fetch('/api/ppstructure/draw', {
        method: 'POST',
        body: drawFormData,
      })
      if (drawResponse.ok) {
        const contentType = drawResponse.headers.get('content-type')
        console.log('Draw response content-type:', contentType)
        console.log('Draw response status:', drawResponse.status)
        
        try {
          if (contentType && contentType.includes('application/json')) {
            // 多页PDF - 返回JSON格式的图片列表
            const drawData = await drawResponse.json()
            console.log('Draw data received (JSON):', {
              file_type: drawData.file_type,
              total_pages: drawData.total_pages,
              processed_pages: drawData.processed_pages,
              max_pages_limit: drawData.max_pages_limit,
              images_count: drawData.images?.length
            })
            
            if (drawData.file_type === 'pdf' && Array.isArray(drawData.images)) {
              console.log(`Processing ${drawData.images.length} images for PDF`)
              const drawImages = drawData.images.map((img: any, idx: number) => {
                console.log(`Image ${idx + 1}: page_number=${img.page_number}, data_length=${img.data?.length || 0}`)
                return `data:image/png;base64,${img.data}`
              })
              console.log(`Setting ${drawImages.length} images`)
              
              // 显示处理信息
              const totalPages = drawData.total_pages || 0
              const processedPages = drawData.processed_pages || 0
              const maxLimit = drawData.max_pages_limit || 0
              
              let messageText = ''
              if (totalPages > processedPages) {
                messageText = `已处理并显示前${processedPages}页绘制结果（共${totalPages}页，限制${maxLimit}页）`
              } else if (totalPages > maxLimit) {
                messageText = `已处理并显示${processedPages}页绘制结果（共${totalPages}页，达到${maxLimit}页限制）`
              } else {
                messageText = `已处理并显示所有${processedPages}页绘制结果`
              }
              
              setMessageWithAutoClear(messageText)
              
              setDrawnImage(drawImages)
            }
          } else {
            // 单页或图像文件 - blob格式（PNG图片流）
            console.log('Processing as blob (single image)')
            const blob = await drawResponse.blob()
            const imageUrl = URL.createObjectURL(blob)
            setDrawnImage(imageUrl)
          }
        } catch (parseError) {
          console.error('Error parsing draw response:', parseError)
        }
      } else {
        console.error('Failed to fetch drawn image:', drawResponse.status, drawResponse.statusText)
      }
    } catch (err) {
      setError('网络错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="layout">
      {message && (
        <div className="global-message-banner">
          {message}
        </div>
      )}

      <ControlBar
        onFileSelect={handleFileSelect}
        file={file}
        loading={loading}
        error={error}
        onUpload={handleUpload}
        onClear={handleClear}
        config={config}
        onConfigChange={handleConfigChange}
        onShowApiModal={() => setShowApiModal(true)}
        pageType="ppstructure"
      />
      
      <Viewer file={file} />
      <ResultPanel result={result} imageFile={file} drawnImage={drawnImage} onMessage={setMessageWithAutoClear} resultType="layout" viewOptions={['json', 'drawn-image', 'markdown']} markdownContent={markdownContent} markdownImageData={markdownImageData} markdownImages={markdownImages} />

      {showApiModal && (
        <div className="api-modal-overlay" onClick={() => setShowApiModal(false)}>
          <div className="api-modal" onClick={(e) => e.stopPropagation()}>
            <div className="api-modal-header">
              <h3>API 文档</h3>
              <button className="close-btn" onClick={() => setShowApiModal(false)}>×</button>
            </div>
            <div className="api-modal-content">
              <div className="api-section">
                <h4>🔗 接口地址</h4>
                <code className="api-url">{apiBaseUrl}</code>
              </div>

              <div className="api-section">
                <h4>📝 PP-Structure V3 布局检测接口</h4>
                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ppstructure</code>
                </div>
                <div className="api-params">
                  <h5>参数：</h5>
                  <ul>
                    <li><code>file</code>: 上传的图像文件或PDF文件</li>
                    <li><code>layout_conf_threshold</code>: 布局检测阈值 (0.0-1.0，默认: 0.5)</li>
                    <li><code>ocr_det_db_thresh</code>: OCR检测阈值 (0.0-1.0，默认: 0.3)</li>
                    <li><code>use_cls</code>: 是否启用方向检测 (true/false，默认: true)</li>
                    <li><code>cls_thresh</code>: 方向检测置信度阈值 (0.0-1.0，默认: 0.9)</li>
                  </ul>
                </div>
              </div>

              <div className="api-section">
                <h4>🎨 可视化接口</h4>
                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ppstructure/draw</code>
                </div>
                <div className="api-params">
                  <h5>参数：</h5>
                  <ul>
                    <li><code>file</code>: 原始图像文件</li>
                    <li><code>layout_result</code>: 布局检测结果的JSON字符串</li>
                  </ul>
                </div>
              </div>

              <div className="api-section">
                <h4>📝 Markdown生成接口</h4>
                <div className="api-endpoint">
                  <code className="method">POST</code>
                  <code className="endpoint">/api/ppstructure/markdown</code>
                </div>
                <div className="api-params">
                  <h5>参数：</h5>
                  <ul>
                    <li><code>file</code>: 原始图像文件</li>
                    <li><code>layout_result</code>: 布局检测结果的JSON字符串</li>
                  </ul>
                  <h5>返回：</h5>
                  <ul>
                    <li><code>markdown</code>: 生成的Markdown文档字符串（包含相对路径图片引用）</li>
                    <li><code>images</code>: 图片数组，每个图片包含 <code>filename</code> 和 <code>data</code>（二进制数据）</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PPStructureV3Page