const db = require('../config/database');
const { v4: uuidv4 } = require('uuid');

class Agent {
  static async create({ agentId, name, type = 'subagent', capabilities = [], metadata = {} }) {
    const result = await db.query(
      `INSERT INTO agents (agent_id, name, type, capabilities, metadata)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING *`,
      [agentId, name, type, capabilities, metadata]
    );
    return result.rows[0];
  }
  
  static async findByAgentId(agentId) {
    const result = await db.query(
      'SELECT * FROM agents WHERE agent_id = $1',
      [agentId]
    );
    return result.rows[0];
  }
  
  static async findAll({ status, type, limit = 50, offset = 0 } = {}) {
    let query = 'SELECT * FROM agents';
    const params = [];
    const conditions = [];
    
    if (status) {
      params.push(status);
      conditions.push(`status = $${params.length}`);
    }
    if (type) {
      params.push(type);
      conditions.push(`type = $${params.length}`);
    }
    
    if (conditions.length > 0) {
      query += ' WHERE ' + conditions.join(' AND ');
    }
    
    query += ' ORDER BY updated_at DESC';
    params.push(limit, offset);
    query += ` LIMIT $${params.length - 1} OFFSET $${params.length}`;
    
    const result = await db.query(query, params);
    return result.rows;
  }
  
  static async updateStatus(agentId, status, socketId = null) {
    const updates = ['status = $2', 'last_active = CURRENT_TIMESTAMP'];
    const params = [agentId, status];
    
    if (socketId) {
      updates.push(`socket_id = $${params.length + 1}`);
      params.push(socketId);
    }
    
    const result = await db.query(
      `UPDATE agents SET ${updates.join(', ')}, updated_at = CURRENT_TIMESTAMP
       WHERE agent_id = $1
       RETURNING *`,
      params
    );
    return result.rows[0];
  }
  
  static async heartbeat(agentId) {
    const result = await db.query(
      `UPDATE agents 
       SET last_heartbeat = CURRENT_TIMESTAMP, last_active = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
       WHERE agent_id = $1
       RETURNING *`,
      [agentId]
    );
    return result.rows[0];
  }
  
  static async findOfflineAgents(timeoutMs) {
    const result = await db.query(
      `SELECT * FROM agents 
       WHERE status = 'online' 
       AND last_heartbeat < NOW() - INTERVAL '${timeoutMs} milliseconds'
       RETURNING *`
    );
    return result.rows;
  }
  
  static async update(agentId, updates) {
    const allowedFields = ['name', 'type', 'capabilities', 'metadata'];
    const setClause = [];
    const params = [agentId];
    
    Object.keys(updates).forEach((key, index) => {
      if (allowedFields.includes(key)) {
        setClause.push(`${key} = $${index + 2}`);
        params.push(updates[key]);
      }
    });
    
    if (setClause.length === 0) return null;
    
    const result = await db.query(
      `UPDATE agents SET ${setClause.join(', ')}, updated_at = CURRENT_TIMESTAMP
       WHERE agent_id = $1
       RETURNING *`,
      params
    );
    return result.rows[0];
  }
  
  static async delete(agentId) {
    await db.query('DELETE FROM agents WHERE agent_id = $1', [agentId]);
    return true;
  }
}

module.exports = Agent;
