import React from 'react'

interface ErrorModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  message: string
  missingFiles?: string[]
}

const ErrorModal: React.FC<ErrorModalProps> = ({ isOpen, onClose, title, message, missingFiles }) => {
  if (!isOpen) return null

  // 获取文件夹路径的函数
  const getFolderPath = (filePath: string) => {
    const parts = filePath.split('/')
    if (parts.length > 1) {
      return parts.slice(0, -1).join('/') + '/'
    }
    return filePath
  }

  // 获取唯一的文件夹列表
  const missingFolders = missingFiles ? [...new Set(missingFiles.map(getFolderPath))] : []

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content error-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <p>{message}</p>
          {missingFolders && missingFolders.length > 0 && (
            <div className="missing-files">
              <h4>缺少以下模型文件夹：</h4>
              <ul>
                {missingFolders.map((folder, index) => (
                  <li key={index}>{folder}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button className="btn btn-primary" onClick={onClose}>确定</button>
        </div>
      </div>
    </div>
  )
}

export default ErrorModal