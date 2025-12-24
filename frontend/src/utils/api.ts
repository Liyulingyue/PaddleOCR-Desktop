/**
 * 获取API基础URL
 * 在开发环境中，API通过代理转发
 * 在生产环境中，需要配置Web服务器转发/api/*到后端
 */
export const getApiBaseUrl = (): string => {
  return window.location.origin
}