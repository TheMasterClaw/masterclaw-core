require('dotenv').config();

module.exports = {
  port: process.env.PORT || 3001,
  env: process.env.NODE_ENV || 'development',
  database: {
    url: process.env.DATABASE_URL,
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
  },
  jwt: {
    secret: process.env.JWT_SECRET || 'dev-secret-change-in-production',
    expiresIn: process.env.JWT_EXPIRES_IN || '7d'
  },
  websocket: {
    heartbeatInterval: parseInt(process.env.WS_HEARTBEAT_INTERVAL) || 30000,
    agentTimeout: parseInt(process.env.AGENT_TIMEOUT) || 60000,
    maxMessageHistory: parseInt(process.env.MAX_MESSAGE_HISTORY) || 1000
  },
  kimi: {
    apiKey: process.env.KIMI_API_KEY,
    apiUrl: process.env.KIMI_API_URL || 'https://api.moonshot.cn/v1'
  },
  logging: {
    level: process.env.LOG_LEVEL || 'info'
  }
};
