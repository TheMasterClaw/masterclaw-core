const db = require('../config/database');
const { v4: uuidv4 } = require('uuid');

class Message {
  static async create({ messageId, fromAgent, toAgent, content, type = 'text', metadata = {} }) {
    const result = await db.query(
      `INSERT INTO messages (message_id, from_agent, to_agent, content, type, metadata)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING *`,
      [messageId || uuidv4(), fromAgent, toAgent, content, type, metadata]
    );
    return result.rows[0];
  }
  
  static async findById(id) {
    const result = await db.query(
      'SELECT * FROM messages WHERE id = $1',
      [id]
    );
    return result.rows[0];
  }
  
  static async findBetweenAgents(agent1, agent2, { limit = 50, offset = 0 } = {}) {
    const result = await db.query(
      `SELECT * FROM messages 
       WHERE (from_agent = $1 AND to_agent = $2) OR (from_agent = $2 AND to_agent = $1)
       ORDER BY created_at DESC
       LIMIT $3 OFFSET $4`,
      [agent1, agent2, limit, offset]
    );
    return result.rows;
  }
  
  static async findForAgent(agentId, { limit = 50, offset = 0, unreadOnly = false } = {}) {
    let query = 'SELECT * FROM messages WHERE to_agent = $1';
    const params = [agentId];
    
    if (unreadOnly) {
      query += ' AND read_at IS NULL';
    }
    
    query += ' ORDER BY created_at DESC LIMIT $2 OFFSET $3';
    params.push(limit, offset);
    
    const result = await db.query(query, params);
    return result.rows;
  }
  
  static async markAsRead(messageId) {
    const result = await db.query(
      `UPDATE messages SET read_at = CURRENT_TIMESTAMP WHERE id = $1 RETURNING *`,
      [messageId]
    );
    return result.rows[0];
  }
  
  static async markAsDelivered(messageId) {
    const result = await db.query(
      `UPDATE messages SET delivered_at = CURRENT_TIMESTAMP WHERE id = $1 RETURNING *`,
      [messageId]
    );
    return result.rows[0];
  }
  
  static async getConversation(agentIds, { limit = 100, before = null } = {}) {
    let query = `
      SELECT * FROM messages 
       WHERE from_agent = ANY($1) AND to_agent = ANY($1)
    `;
    const params = [agentIds];
    
    if (before) {
      query += ` AND created_at < $${params.length + 1}`;
      params.push(before);
    }
    
    query += ` ORDER BY created_at DESC LIMIT $${params.length + 1}`;
    params.push(limit);
    
    const result = await db.query(query, params);
    return result.rows.reverse(); // Return in chronological order
  }
  
  static async getUnreadCount(agentId) {
    const result = await db.query(
      'SELECT COUNT(*) FROM messages WHERE to_agent = $1 AND read_at IS NULL',
      [agentId]
    );
    return parseInt(result.rows[0].count);
  }
}

module.exports = Message;
