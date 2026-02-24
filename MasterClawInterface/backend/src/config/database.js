const config = require('./config');

// Use in-memory database if no DATABASE_URL is set or USE_MEMORY_DB is true
if (!config.database.url || process.env.USE_MEMORY_DB === 'true') {
  console.log('📦 Using in-memory database (development mode)');
  module.exports = require('./database-memory');
} else {
  console.log('🐘 Using PostgreSQL database');
  module.exports = require('./database-pg');
}