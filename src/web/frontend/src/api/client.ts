import axios from 'axios'

/** 与 Vite 代理一致：开发环境 `/api` 转发到后端。 */
export const api = axios.create({
  baseURL: '/api',
})
