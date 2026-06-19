interface EnvConfig {
  apiUrl: string;
  appName: string;
  isDev: boolean;
}

function loadEnv(): EnvConfig {
  const apiUrl = import.meta.env.VITE_API_URL ?? '/api/v1';
  const appName = import.meta.env.VITE_APP_NAME ?? 'J.A.R.V.I.S';
  const isDev = import.meta.env.MODE === 'development';

  if (typeof apiUrl !== 'string' || !apiUrl) {
    throw new Error('VITE_API_URL must be a non-empty string');
  }

  return { apiUrl, appName, isDev };
}

export const env = loadEnv();
