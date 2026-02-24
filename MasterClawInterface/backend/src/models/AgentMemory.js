const db = require('../config/database');

class AgentMemory {
  // Log a thought, observation, need, or decision
  static async log({ agentId, memoryType, content, context = {}, importance = 1, relatedMessageId = null }) {
    const result = await db.query(
      `INSERT INTO agent_memory (agent_id, memory_type, content, context, importance, related_message_id)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING *`,
      [agentId, memoryType, content, context, importance, relatedMessageId]
    );
    return result.rows[0];
  }
  
  // Get recent memories for an agent
  static async getForAgent(agentId, { types = [], limit = 50, minImportance = 1 } = {}) {
    let query = `
      SELECT am.*, m.content as related_message_content
      FROM agent_memory am
      LEFT JOIN messages m ON am.related_message_id = m.id
      WHERE am.agent_id = $1 AND am.importance >= $2
    `;
    const params = [agentId, minImportance];
    
    if (types.length > 0) {
      query += ` AND am.memory_type = ANY($${params.length + 1})`;
      params.push(types);
    }
    
    query += ` ORDER BY am.created_at DESC LIMIT $${params.length + 1}`;
    params.push(limit);
    
    const result = await db.query(query, params);
    return result.rows;
  }
  
  // Get agent's current context (recent high-importance memories)
  static async getContext(agentId, { limit = 10 } = {}) {
    const result = await db.query(
      `SELECT * FROM agent_memory 
       WHERE agent_id = $1 AND importance >= 3
       ORDER BY created_at DESC
       LIMIT $2`,
      [agentId, limit]
    );
    return result.rows;
  }
  
  // Get all "needs" for an agent (things the agent needs help with)
  static async getNeeds(agentId, { unmetOnly = true, limit = 20 } = {}) {
    let query = `
      SELECT am.*, m.content as trigger_message
      FROM agent_memory am
      LEFT JOIN messages m ON am.related_message_id = m.id
      WHERE am.agent_id = $1 AND am.memory_type = 'need'
    `;
    const params = [agentId];
    
    if (unmetOnly) {
      // Needs that don't have a 'completed' or 'addressed' status in context
      query += ` AND (am.context->>'status' IS NULL OR am.context->>'status' != 'addressed')`;
    }
    
    query += ` ORDER BY am.importance DESC, am.created_at DESC LIMIT $${params.length + 1}`;
    params.push(limit);
    
    const result = await db.query(query, params);
    return result.rows;
  }
  
  // Mark a need as addressed
  static async addressNeed(memoryId, resolution = {}) {
    const result = await db.query(
      `UPDATE agent_memory 
       SET context = context || $2::jsonb
       WHERE id = $1
       RETURNING *`,
      [memoryId, JSON.stringify({ status: 'addressed', resolved_at: new Date().toISOString(), ...resolution })]
    );
    return result.rows[0];
  }
  
  // Search memories by content
  static async search(agentId, query, { limit = 20 } = {}) {
    const result = await db.query(
      `SELECT * FROM agent_memory 
       WHERE agent_id = $1 AND content ILIKE $2
       ORDER BY created_at DESC
       LIMIT $3`,
      [agentId, `%${query}%`, limit]
    );
    return result.rows;
  }
  
  // Get memory statistics for an agent
  static async getStats(agentId) {
    const result = await db.query(
      `SELECT 
        memory_type,
        COUNT(*) as count,
        AVG(importance) as avg_importance
       FROM agent_memory 
       WHERE agent_id = $1
       GROUP BY memory_type`,
      [agentId]
    );
    return result.rows;
  }
  
  // Delete old memories (for cleanup)
  static async cleanup(agentId, olderThanDays = 30, maxImportance = 2) {
    const result = await db.query(
      `DELETE FROM agent_memory 
       WHERE agent_id = $1 
       AND created_at < NOW() - INTERVAL '${olderThanDays} days'
       AND importance <= $2
       RETURNING *`,
      [agentId, maxImportance]
    );
    return result.rows;
  }
}

module.exports = AgentMemory;
