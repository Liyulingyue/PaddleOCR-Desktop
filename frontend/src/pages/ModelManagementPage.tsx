import React, { useState, useEffect } from 'react';
import { getCachedApiBaseUrl } from '../utils/api';
import '../styles/model-management.css';

interface ModelInfo {
  name: string;
  modelscope_id: string;
  local_path: string;
  is_downloaded: boolean;
  size: number;
}

const ModelManagementPage: React.FC = () => {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set());
  const [batchDownloading, setBatchDownloading] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const baseUrl = await getCachedApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/models/list`);
      if (response.ok) {
        const data = await response.json();
        setModels(data);
      }
    } catch (error) {
      console.error('Failed to fetch models:', error);
    } finally {
      setLoading(false);
    }
  };

  const downloadModel = async (modelName: string) => {
    setDownloading(modelName);
    try {
      const baseUrl = await getCachedApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/models/download/${modelName}`, {
        method: 'POST',
      });
      if (response.ok) {
        // 重新获取模型列表
        await fetchModels();
      } else {
        alert(`下载失败: ${await response.text()}`);
      }
    } catch (error) {
      console.error('Failed to download model:', error);
      alert('下载失败，请检查网络连接');
    } finally {
      setDownloading(null);
    }
  };

  const deleteModel = async (modelName: string) => {
    setDeleting(modelName);
    try {
      const baseUrl = await getCachedApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/models/delete/${modelName}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        // 重新获取模型列表
        await fetchModels();
        setDeleteConfirm(null);
      } else {
        alert(`删除失败: ${await response.text()}`);
      }
    } catch (error) {
      console.error('Failed to delete model:', error);
      alert('删除失败，请重试');
    } finally {
      setDeleting(null);
    }
  };

  const batchDownload = async () => {
    if (selectedModels.size === 0) {
      alert('请先选择要下载的模型');
      return;
    }

    const modelsToDownload = Array.from(selectedModels).filter(
      modelName => !models.find(m => m.name === modelName)?.is_downloaded
    );

    if (modelsToDownload.length === 0) {
      alert('选中的模型都已下载');
      return;
    }

    setBatchDownloading(true);
    try {
      const baseUrl = await getCachedApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/models/batch-download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(modelsToDownload),
      });

      if (response.ok) {
        const result = await response.json();
        const failed = result.results.filter((r: any) => !r.success);
        if (failed.length > 0) {
          alert(`${failed.length}个模型下载失败`);
        }
        await fetchModels();
        setSelectedModels(new Set());
      } else {
        alert(`批量下载失败: ${await response.text()}`);
      }
    } catch (error) {
      console.error('Batch download failed:', error);
      alert('批量下载失败，请检查网络连接');
    } finally {
      setBatchDownloading(false);
    }
  };

  const batchDelete = async () => {
    if (selectedModels.size === 0) {
      alert('请先选择要删除的模型');
      return;
    }

    const modelsToDelete = Array.from(selectedModels).filter(
      modelName => models.find(m => m.name === modelName)?.is_downloaded
    );

    if (modelsToDelete.length === 0) {
      alert('选中的模型中没有已下载的模型');
      return;
    }

    setDeleteConfirm(`batch-${modelsToDelete.join(',')}`);
  };

  const confirmBatchDelete = async () => {
    const modelNames = deleteConfirm!.replace('batch-', '').split(',');
    setBatchDeleting(true);

    try {
      const baseUrl = await getCachedApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/models/batch-delete`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(modelNames),
      });

      if (response.ok) {
        const result = await response.json();
        const failed = result.results.filter((r: any) => !r.success);
        if (failed.length > 0) {
          alert(`${failed.length}个模型删除失败`);
        }
        await fetchModels();
        setSelectedModels(new Set());
        setDeleteConfirm(null);
      } else {
        alert(`批量删除失败: ${await response.text()}`);
      }
    } catch (error) {
      console.error('Batch delete failed:', error);
      alert('批量删除失败');
    } finally {
      setBatchDeleting(false);
    }
  };

  const toggleModelSelection = (modelName: string) => {
    const newSelected = new Set(selectedModels);
    if (newSelected.has(modelName)) {
      newSelected.delete(modelName);
    } else {
      newSelected.add(modelName);
    }
    setSelectedModels(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedModels.size === models.length) {
      setSelectedModels(new Set());
    } else {
      setSelectedModels(new Set(models.map(m => m.name)));
    }
  };

  const confirmDelete = (modelName: string) => {
    setDeleteConfirm(modelName);
  };

  const cancelDelete = () => {
    setDeleteConfirm(null);
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return <div className="page-container">加载中...</div>;
  }

  const downloadableSelected = Array.from(selectedModels).filter(
    modelName => !models.find(m => m.name === modelName)?.is_downloaded
  );

  const deletableSelected = Array.from(selectedModels).filter(
    modelName => models.find(m => m.name === modelName)?.is_downloaded
  );

  return (
    <div className="page-container">
      <h1>模型管理</h1>

      {/* 批量操作栏 */}
      <div className="batch-actions">
        <div className="select-all">
          <input
            type="checkbox"
            checked={selectedModels.size === models.length && models.length > 0}
            onChange={toggleSelectAll}
            id="select-all"
          />
          <label htmlFor="select-all">全选 ({selectedModels.size}/{models.length})</label>
        </div>

        <div className="batch-buttons">
          <button
            onClick={batchDownload}
            disabled={batchDownloading || downloadableSelected.length === 0}
            className="batch-download-btn"
            title={downloadableSelected.length === 0 ? '没有选中需要下载的模型' : `下载选中 (${downloadableSelected.length})`}
          >
            {batchDownloading ? '批量下载中...' : `下载选中 (${downloadableSelected.length})`}
          </button>

          <button
            onClick={batchDelete}
            disabled={batchDeleting || deletableSelected.length === 0}
            className="batch-delete-btn"
            title={deletableSelected.length === 0 ? '没有选中已下载的模型' : `删除选中 (${deletableSelected.length})`}
          >
            {batchDeleting ? '批量删除中...' : `删除选中 (${deletableSelected.length})`}
          </button>
        </div>
      </div>

      <div className="model-list">
        {models.map((model) => (
          <div key={model.name} className="model-item">
            <div className="model-selection">
              <input
                type="checkbox"
                checked={selectedModels.has(model.name)}
                onChange={() => toggleModelSelection(model.name)}
                id={`model-${model.name}`}
              />
            </div>

            <div className="model-info">
              <h3>{model.name}</h3>
              <p>ModelScope ID: {model.modelscope_id}</p>
              <p>本地路径: {model.local_path}</p>
              <p>状态: {model.is_downloaded ? `已下载${model.size > 0 ? ` (${formatSize(model.size)})` : ''}` : '未下载'}</p>
            </div>

            <div className="model-actions">
              {!model.is_downloaded && (
                <button
                  onClick={() => downloadModel(model.name)}
                  disabled={downloading === model.name}
                  className="download-btn"
                >
                  {downloading === model.name ? '下载中...' : '下载'}
                </button>
              )}
              {model.is_downloaded && (
                <button
                  onClick={() => confirmDelete(model.name)}
                  disabled={deleting === model.name}
                  className="delete-btn"
                >
                  {deleting === model.name ? '删除中...' : '删除'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 删除确认对话框 */}
      {deleteConfirm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>确认删除</h3>
            {deleteConfirm.startsWith('batch-') ? (
              <p>确定要删除选中的 {deleteConfirm.replace('batch-', '').split(',').length} 个模型吗？此操作无法撤销。</p>
            ) : (
              <p>确定要删除模型 "{deleteConfirm}" 吗？此操作无法撤销。</p>
            )}
            <div className="modal-actions">
              <button onClick={cancelDelete} className="cancel-btn">
                取消
              </button>
              <button
                onClick={deleteConfirm.startsWith('batch-') ? confirmBatchDelete : () => deleteModel(deleteConfirm)}
                className="confirm-delete-btn"
              >
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelManagementPage;