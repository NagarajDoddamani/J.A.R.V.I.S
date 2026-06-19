import axios from 'axios';

import { env } from '@/config/env';

const apiClient = axios.create({
  baseURL: env.apiUrl,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const normalized = {
      message: error.response?.data?.detail ?? error.message ?? 'Unknown error',
      code: error.code ?? 'UNKNOWN',
      status: error.response?.status ?? 0,
    };
    return Promise.reject(normalized);
  },
);

export { apiClient };
