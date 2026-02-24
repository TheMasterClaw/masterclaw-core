const { Pool } = require('pg');
const config = require('./config');

const pool = new Pool({
  connectionString: config.database.url,
  ssl: config.database.ssl
});

pool.on('error', (err) => {
  console.error('Unexpected database error:', err);
  process.exit(-1);
});

module.exports = {
  pool,
  query: (text, params) => pool.query(text, params),
  
  // Transaction helper
  transaction: async (callback) => {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      const result = await callback(client);
      await client.query('COMMIT');
      return result;
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }
};