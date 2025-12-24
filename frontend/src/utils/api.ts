import { invoke } from '@tauri-apps/api/core';

/**
 * 获取API基础URL
 * 在开发环境中，API通过代理转发
 * 在生产环境中，通过Tauri启动后端并获取端口
 */
export const getApiBaseUrl = async (): Promise<string> => {
  // 在开发环境中使用代理
  if (import.meta.env.DEV) {
    return window.location.origin;
  }

  // 在生产环境中，通过Tauri命令启动后端并获取端口
  try {
    const port: number = await invoke('start_backend');
    return `http://localhost:${port}`;
  } catch (error) {
    console.error('Failed to start backend via Tauri:', error);
    // 降级到端口扫描方案
    return await fallbackPortDiscovery();
  }
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