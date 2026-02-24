const db = require('../config/database');
const { v4: uuidv4 } = require('uuid');

class AgentJob {
  static async create({ jobId, agentId, title, description, priority = 2, assignedBy = null }) {
    const result = await db.query(
      `INSERT INTO agent_jobs (job_id, agent_id, title, description, priority, assigned_by)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING *`,
      [jobId || uuidv4(), agentId, title, description, priority, assignedBy]
    );
    return result.rows[0];
  }
  
  static async findByJobId(jobId) {
    const result = await db.query(
      'SELECT * FROM agent_jobs WHERE job_id = $1',
      [jobId]
    );
    return result.rows[0];
  }
  
  static async findForAgent(agentId, { status, limit = 50 } = {}) {
    let query = 'SELECT * FROM agent_jobs WHERE agent_id = $1';
    const params = [agentId];
    
    if (status) {
      query += ' AND status = $2';
      params.push(status);
    }
    
    query += ' ORDER BY priority ASC, created_at DESC LIMIT $' + (params.length + 1);
    params.push(limit);
    
    const result = await db.query(query, params);
    return result.rows;
  }
  
  static async updateStatus(jobId, status, result = null) {
    const updates = ['status = $2'];
    const params = [jobId, status];
    
    if (status === 'in_progress') {
      updates.push('started_at = CURRENT_TIMESTAMP');
    } else if (['completed', 'failed', 'cancelled'].includes(status)) {
      updates.push('completed_at = CURRENT_TIMESTAMP');
    }
    
    if (result) {
      updates.push(`result = $${params.length + 1}`);
      params.push(result);
    }
    
    updates.push('updated_at = CURRENT_TIMESTAMP');
    
    const queryResult = await db.query(
      `UPDATE agent_jobs SET ${updates.join(', ')} WHERE job_id = $1 RETURNING *`,
      params
    );
    return queryResult.rows[0];
  }
  
  static async getPendingJobs(agentId = null) {
    let query = `
      SELECT j.*, a.name as agent_name 
      FROM agent_jobs j
      JOIN agents a ON j.agent_id = a.agent_id
      WHERE j.status IN ('pending', 'in_progress')
    `;
    const params = [];
    
    if (agentId) {
      query += ' AND j.agent_id = $1';
      params.push(agentId);
    }
    
    query += ' ORDER BY j.priority ASC, j.created_at ASC';
    
    const result = await db.query(query, params);
    return result.rows;
  }
  
  static async delete(jobId) {
    await db.query('DELETE FROM agent_jobs WHERE job_id = $1', [jobId]);
    return true;
  }
}

module.exports = AgentJob;
