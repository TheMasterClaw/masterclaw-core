const { createTables } = require('../src/models');

async function setupTestDb() {
  await createTables();
  console.log('✅ Test database setup complete');
}

module.exports = { setupTestDb };
