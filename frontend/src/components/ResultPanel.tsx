import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import JSZip from 'jszip'

interface ResultPanelProps {
  result: any
  imageFile: File | null
  drawnImage: string | any[] | null
  onMessage: (message: string) => void
  resultType?: string
  viewOptions?: string[]
  markdownContent?: string | null
  markdownImageData?: string | null
  markdownImages?: { [key: string]: string } | null
}

// 从OCR结果中提取纯文本
function extractTextFromResult(result: any, resultType: string = 'ocr'): string {
  if (!result) return ''
  
  if (resultType === 'layout') {
    // 布局检测结果
    if (Array.isArray(result)) {
      const layoutLines: string[] = []
      for (const region of result) {
        if (region && typeof region === 'object' && 'type' in region && 'bbox' in region) {
          const bbox = region.bbox
          const type = region.type
          const conf = region.confidence ? region.confidence.toFixed(3) : 'N/A'
          layoutLines.push(`${type}: [${bbox.join(', ')}] (conf: ${conf})`)
        }
      }
      return layoutLines.join('\n')
    }
    return ''
  }
  
  const textLines: string[] = []
  
  // 检查是否为多页PDF结果
  if (Array.isArray(result) && result.length > 0 && typeof result[0] === 'object' && 'page' in result[0]) {
    // 多页PDF结果 - pipeline格式
    for (const pageData of result) {
      const pageResults = pageData.results
      if (pageResults && Array.isArray(pageResults)) {
        for (const item of pageResults) {
          if (item && typeof item === 'object' && 'text' in item) {
            const text = item.text
            if (text && text.trim()) {
              textLines.push(text)
            }
          }
        }
      }
    }
  } else if (Array.isArray(result)) {
    // 单页结果 - pipeline格式
    for (const item of result) {
      if (item && typeof item === 'object' && 'text' in item) {
        const text = item.text
        if (text && text.trim()) {
          textLines.push(text)
        }
      }
    }
  }
  
  return textLines.join('\n')
}

// @ts-ignore
function ResultPanel({ result, imageFile, drawnImage, onMessage, resultType = 'ocr', viewOptions, markdownContent, markdownImageData, markdownImages }: ResultPanelProps) {
  const defaultViewOptions = ['json', 'drawn-image']
  if (resultType !== 'layout') {
    defaultViewOptions.push('ocr-text')
  }
  const availableViews = viewOptions || defaultViewOptions
  
  const [view, setView] = useState<string>(availableViews[0])

  // 处理markdown内容，将图片引用替换为实际的data URI
  const processMarkdownContent = (content: string | null): string => {
    if (!content) return content || ''
    
    let processedContent = content
    
    console.log('Processing markdown content, markdownImages:', markdownImages)
    console.log('Original content sample:', content.substring(0, 500))
    
    // 将相对路径的图片引用替换为base64 data URI
    if (markdownImages) {
      Object.entries(markdownImages).forEach(([filename, base64Data]) => {
        const regex = new RegExp(`\\(images/${filename}\\)`, 'g')
        const beforeCount = (processedContent.match(regex) || []).length
        processedContent = processedContent.replace(regex, `(${base64Data})`)
        const afterCount = (processedContent.match(new RegExp(`\\(data:image/png;base64,`, 'g')) || []).length
        console.log(`Replaced images/${filename}: ${beforeCount} -> ${afterCount} replacements`)
      })
    }
    
    // 兼容旧格式
    if (markdownImageData) {
      processedContent = processedContent.replace(
        /\(original_image\.png\)/g, 
        `(data:image/png;base64,${markdownImageData})`
      )
    }
    
    console.log('Processed content sample:', processedContent.substring(0, 500))
    return processedContent
  }



  const copyResult = async () => {
    try {
      let contentToCopy: string
      let contentType: string
      
      if (view === 'ocr-text') {
        // 复制纯文本内容
        contentToCopy = extractTextFromResult(result, resultType)
        contentType = '纯文本'
      } else if (view === 'markdown') {
        // 复制markdown内容
        contentToCopy = markdownContent || 'No markdown content available'
        contentType = 'Markdown'
        if (!markdownContent) {
          onMessage('警告：Markdown内容为空，将复制占位符文本')
        }
      } else if (view === 'drawn-image') {
        // 图像视图无法复制到剪贴板
        onMessage('图像无法复制到剪贴板，请使用下载功能保存图像')
        setTimeout(() => onMessage(''), 3000)
        return
      } else {
        // 复制JSON格式的结果
        contentToCopy = JSON.stringify(result || {}, null, 2)
        contentType = 'JSON'
      }
      
      await navigator.clipboard.writeText(contentToCopy)
      onMessage(`已复制${contentType}内容到剪贴板`)
      setTimeout(() => onMessage(''), 3000) // 3秒后自动隐藏
    } catch (e) {
      onMessage('复制失败')
      setTimeout(() => onMessage(''), 2000)
    }
  }

  const downloadResult = () => {
    let content: string
    let filename: string
    let mimeType: string
    let contentType: string
    
    if (view === 'ocr-text') {
      // 下载纯文本内容
      content = extractTextFromResult(result, resultType)
      filename = resultType === 'layout' ? 'layout_result.txt' : 'ocr_result.txt'
      mimeType = 'text/plain'
      contentType = '纯文本'
    } else if (view === 'markdown') {
      // 下载markdown内容和图片的压缩包
      const zip = new JSZip()
      
      // 添加markdown文件
      const mdContent = markdownContent || '# Error\n\nNo markdown content available'
      zip.file('document.md', mdContent)
      
      // 添加单独的图片文件（如果有的话）
      if (markdownImages) {
        Object.entries(markdownImages).forEach(([filename, base64Data]) => {
          // 从base64数据中提取实际的图片数据
          const base64Match = base64Data.match(/^data:image\/png;base64,(.+)$/)
          if (base64Match) {
            const imageBlob = new Blob(
              [Uint8Array.from(atob(base64Match[1]), c => c.charCodeAt(0))], 
              { type: 'image/png' }
            )
            // 将图片保存在images目录中，与markdown中的引用路径匹配
            zip.file(`images/${filename}`, imageBlob)
          }
        })
      }
      
      // 生成并下载压缩包
      zip.generateAsync({ type: 'blob' }).then((content) => {
        const url = URL.createObjectURL(content)
        const a = document.createElement('a')
        a.href = url
        a.download = 'document_with_images.zip'
        a.click()
        URL.revokeObjectURL(url)
        onMessage('已下载Markdown文档和图片压缩包')
        setTimeout(() => onMessage(''), 3000)
      })
      return
      if (drawnImage && typeof drawnImage === 'string') {
        // 单张图片，直接下载
        const a = document.createElement('a')
        a.href = drawnImage as string
        a.download = resultType === 'layout' ? 'layout_visualization.png' : 'ocr_visualization.png'
        a.click()
        onMessage('已下载图像文件')
        setTimeout(() => onMessage(''), 3000)
        return
      } else if (drawnImage && Array.isArray(drawnImage) && drawnImage!.length > 0) {
        // 多页PDF图片，下载第一页作为示例
        const a = document.createElement('a')
        a.href = (drawnImage as any[])[0]?.image || ''
        a.download = 'document_visualization_page1.png'
        a.click()
        onMessage('已下载第一页图像文件')
        setTimeout(() => onMessage(''), 3000)
        return
      }
      // 如果没有图片，回退到JSON
      content = JSON.stringify(result || {}, null, 2)
      filename = resultType === 'layout' ? 'layout_result.json' : 'ocr_result.json'
      mimeType = 'application/json'
      contentType = 'JSON'
    } else {
      // 下载JSON格式的结果
      content = JSON.stringify(result || {}, null, 2)
      filename = resultType === 'layout' ? 'layout_result.json' : 'ocr_result.json'
      mimeType = 'application/json'
      contentType = 'JSON'
    }
    
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    
    onMessage(`已下载${contentType}文件`)
    setTimeout(() => onMessage(''), 3000)
  }

  return (
    <aside className="result-panel">
      <div className="result-panel-header">
        <h3>解析结果</h3>
        <div className="header-controls">
          <div className="action-buttons">
            <button className="action-btn copy-btn" onClick={copyResult} title="复制结果">📋复制</button>
            <button className="action-btn download-btn" onClick={downloadResult} title="下载结果">💾下载</button>
          </div>
          <label htmlFor="view-select" className="sr-only">结果格式</label>
          <select
            id="view-select"
            className="view-select"
            value={view}
            onChange={(e) => setView(e.target.value)}
          >
            {availableViews.map(option => {
              const labels: Record<string, string> = {
                'json': 'JSON',
                'drawn-image': '绘制图像',
                'ocr-text': '纯文本',
                'markdown': 'Markdown'
              }
              return (
                <option key={option} value={option}>
                  {labels[option] || option}
                </option>
              )
            })}
          </select>
        </div>
      </div>

      <div className="result-body">
        {result ? (
          view === 'json' ? (
            <pre>{JSON.stringify(result, null, 2)}</pre>
          ) : view === 'markdown' ? (
            <div className="markdown-content">
      {markdownContent ? (
        <div className="markdown-rendered">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw]}
            components={{
              img: ({ src, alt, ...props }) => {
                console.log('Image in markdown:', { src: src?.substring(0, 50) + '...', alt })
                // 确保base64图片能正确渲染
                if (src && src.startsWith('data:image/')) {
                  return <img src={src} alt={alt || 'Image'} {...props} style={{ maxWidth: '100%', height: 'auto', border: '1px solid #ddd', borderRadius: '4px' }} />
                }
                return <img src={src} alt={alt} {...props} />
              }
            }}
            urlTransform={(url) => {
              // 确保data URL被正确处理
              if (url.startsWith('data:')) {
                return url
              }
              return url
            }}
            skipHtml={false}
          >
            {processMarkdownContent(markdownContent)}
          </ReactMarkdown>
        </div>
              ) : (
                <p>Loading markdown content...</p>
              )}
            </div>
          ) : view === 'ocr-text' ? (
            <div className="ocr-text">
              <pre>{extractTextFromResult(result, resultType)}</pre>
            </div>
          ) : (
            <div className="drawn-image">
              {drawnImage ? (
                Array.isArray(drawnImage) ? (
                  // 多张图片（多页PDF文件）
                  <div className="pdf-images">
                    {drawnImage.map((imageUrl: string, index: number) => (
                      <div key={index} className="pdf-page">
                        <div className="page-header">第 {index + 1} 页</div>
                        <img 
                          src={imageUrl} 
                          alt={`结构分析结果 - 第${index + 1}页`} 
                          style={{ maxWidth: '100%', height: 'auto', border: '1px solid #ddd' }} 
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  // 单张图片（普通图像文件或单页PDF）
                  <img src={drawnImage} alt="结构分析结果" style={{ maxWidth: '100%', height: 'auto' }} />
                )
              ) : (
                <p>绘制图像加载中...</p>
              )}
            </div>
          )
        ) : (
          <div className="empty-state">
            <p>尚无解析结果</p>
          </div>
        )}
      </div>
    </aside>
  )
}

export default ResultPanel