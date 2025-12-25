import { invoke } from '@tauri-apps/api/core';

/**
 * 检测是否在 Tauri 环境中
 */
export const isTauri = () => {
  return typeof window !== 'undefined' && '__TAURI__' in window;
};

/**
 * 获取API基础URL
 * 在开发环境中，API通过代理转发
 * 在生产环境中，通过Tauri获取后端URL
 */
export const getApiBaseUrl = async (): Promise<string> => {
  // 在开发环境中使用代理
  if (import.meta.env.DEV) {
    return window.location.origin;
  }

  // 在Tauri环境中，通过invoke获取后端URL
  if (isTauri()) {
    try {
      // 首先尝试启动后端（如果还没启动）
      await invoke('start_backend');

      // 然后获取后端URL
      const backendUrl: string = await invoke('get_backend_url');
      return backendUrl;
    } catch (error) {
      console.error('Failed to get backend URL via Tauri:', error);
      // 降级到默认URL
      return 'http://127.0.0.1:8000';
    }
  }

  // Web环境下的降级方案
  return await fallbackPortDiscovery();
};

// 降级方案：扫描端口
const fallbackPortDiscovery = async (): Promise<string> => {
  console.log('Using fallback port discovery...');

  // 首先尝试读取port.json文件
  try {
    const portResponse = await fetch('/port.json');
    if (portResponse.ok) {
      const portData = await portResponse.json();
      const port = portData.port;
      const url = `http://localhost:${port}`;
      // 验证端口是否可用
      const healthResponse = await fetch(`${url}/api/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(1000)
      });
      if (healthResponse.ok) {
        return url;
      }
    }
  } catch (error) {
    console.log('Failed to read port.json:', error);
  }

  // 如果port.json不可用，扫描端口 (8000-8099)
  for (let port = 8000; port < 8100; port++) {
    try {
      const url = `http://localhost:${port}`;
      const response = await fetch(`${url}/api/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(500) // 0.5秒超时
      });
      if (response.ok) {
        return url;
      }
    } catch (error) {
      continue;
    }
  }

  // 如果都失败了，返回默认值
  console.warn('Could not find backend server, using default URL');
  return 'http://localhost:8000';
};

// 缓存的API URL
let cachedApiUrl: string | null = null;

/**
 * 获取缓存的API URL，如果没有则异步获取
 */
export const getCachedApiBaseUrl = async (): Promise<string> => {
  if (!cachedApiUrl) {
    cachedApiUrl = await getApiBaseUrl();
  }
  return cachedApiUrl;
};