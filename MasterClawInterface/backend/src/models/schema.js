const db = require('../config/database');

const createTables = async () => {
  // Skip table creation for in-memory database
  if (process.env.USE_MEMORY_DB === 'true' || !process.env.DATABASE_URL) {
    console.log('✅ Using in-memory database (no table creation needed)');
    return;
  }
  
  const client = await db.pool.connect();
  
  try {
    await client.query('BEGIN');
    
    // Agents registry
    await client.query(`
      CREATE TABLE IF NOT EXISTS agents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        agent_id VARCHAR(100) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        type VARCHAR(50) DEFAULT 'subagent' CHECK (type IN ('master', 'subagent', 'specialist', 'tool')),
        status VARCHAR(20) DEFAULT 'offline' CHECK (status IN ('online', 'offline', 'busy', 'away')),
        capabilities TEXT[],
        metadata JSONB DEFAULT '{}',
        socket_id VARCHAR(255),
        last_heartbeat TIMESTAMP,
        last_active TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Messages table
    await client.query(`
      CREATE TABLE IF NOT EXISTS messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        message_id VARCHAR(100) UNIQUE NOT NULL,
        from_agent VARCHAR(100) NOT NULL,
        to_agent VARCHAR(100) NOT NULL,
        content TEXT NOT NULL,
        type VARCHAR(20) DEFAULT 'text' CHECK (type IN ('text', 'command', 'status', 'memory', 'error', 'system')),
        metadata JSONB DEFAULT '{}',
        read_at TIMESTAMP,
        delivered_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Agent memory/thoughts logging
    await client.query(`
      CREATE TABLE IF NOT EXISTS agent_memory (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        agent_id VARCHAR(100) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
        memory_type VARCHAR(50) NOT NULL CHECK (memory_type IN ('thought', 'job', 'need', 'observation', 'decision')),
        content TEXT NOT NULL,
        context JSONB DEFAULT '{}',
        importance INTEGER DEFAULT 1 CHECK (importance BETWEEN 1 AND 5),
        related_message_id UUID REFERENCES messages(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Agent jobs/tasks
    await client.query(`
      CREATE TABLE IF NOT EXISTS agent_jobs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        job_id VARCHAR(100) UNIQUE NOT NULL,
        agent_id VARCHAR(100) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),
        priority INTEGER DEFAULT 2 CHECK (priority BETWEEN 1 AND 5),
        assigned_by VARCHAR(100),
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        result JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Conversations (grouped messages)
    await client.query(`
      CREATE TABLE IF NOT EXISTS conversations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        conversation_id VARCHAR(100) UNIQUE NOT NULL,
        participant_ids TEXT[] NOT NULL,
        title VARCHAR(255),
        is_group BOOLEAN DEFAULT false,
        metadata JSONB DEFAULT '{}',
        last_message_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Agent capabilities/skills
    await client.query(`
      CREATE TABLE IF NOT EXISTS agent_capabilities (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        agent_id VARCHAR(100) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
        capability VARCHAR(100) NOT NULL,
        description TEXT,
        parameters JSONB DEFAULT '{}',
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Indexes
    await client.query(`CREATE INDEX IF NOT EXISTS idx_agents_agent_id ON agents(agent_id)`);
    await client.query(`CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)`);
    await client.query(`CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(type)`);
    await client.query(`CREATE INDEX IF NOT EXISTS idx_messages_from ON messages(from_agent)`);
    await client.query(`CREATE INDEX IF NOT EXISTS idx_messages_to ON messages(to_agent)`);
    await client.query(`CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)`);
    await client.query(`CREATE INDEX IF NOT EXISTS idx_agent_memory_agent ON agent_memory(agent_id)`);
    await client.query(`CREATE INDEX IF NOT EXISTS idx_agent_memory_type ON agent_memory(memory_type)`);
    await client.query(`CREATE INDEX IF NOT EXISTS idx_agent_jobs_agent ON agent_jobs(agent_id)`);
    await client.query(`CREATE INDEX IF NOT EXISTS idx_agent_jobs_status ON agent_jobs(status)`);
    await client.query(`CREATE INDEX IF NOT EXISTS idx_conversations_participants ON conversations USING GIN(participant_ids)`);
    
    await client.query('COMMIT');
    console.log('✅ Database tables created successfully');
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('❌ Error creating tables:', err);
    throw err;
  } finally {
    client.release();
  }
};

module.exports = { createTables };