// In-memory database fallback for development/testing
// Mimics the pg pool interface for seamless swapping

class InMemoryDB {
  constructor() {
    this.tables = {
      agents: [],
      messages: [],
      agent_memory: [],
      agent_jobs: [],
      conversations: [],
      agent_capabilities: []
    };
    this.idCounters = {};
  }

  generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  async query(text, params = []) {
    // Simple SQL parsing for basic operations
    const lowerText = text.toLowerCase();
    
    // SELECT
    if (lowerText.startsWith('select')) {
      return this.handleSelect(text, params);
    }
    
    // INSERT
    if (lowerText.startsWith('insert')) {
      return this.handleInsert(text, params);
    }
    
    // UPDATE
    if (lowerText.startsWith('update')) {
      return this.handleUpdate(text, params);
    }
    
    // DELETE
    if (lowerText.startsWith('delete')) {
      return this.handleDelete(text, params);
    }
    
    return { rows: [] };
  }

  handleSelect(text, params) {
    // Extract table name (simple regex)
    const fromMatch = text.match(/from\s+(\w+)/i);
    if (!fromMatch) return { rows: [] };
    
    const tableName = fromMatch[1];
    let rows = [...(this.tables[tableName] || [])];
    
    // Handle WHERE conditions (simple implementation)
    if (text.toLowerCase().includes('where')) {
      // Extract conditions - match everything after WHERE until end or keywords
      const whereMatch = text.match(/where\s+(.+?)(?:\s+order\s+by|\s+limit|\s+group\s+by|$)/i);
      if (whereMatch) {
        const fullCondition = whereMatch[1].trim();
        
        // Split by AND to handle multiple conditions
        const conditions = fullCondition.split(/\s+and\s+/i);
        
        conditions.forEach((condition, condIdx) => {
          condition = condition.trim();
          
          // Find all $N placeholders in this condition
          const placeholders = [...condition.matchAll(/\$(\d+)/g)];
          if (placeholders.length === 0) return;
          
          // Get the first placeholder value for this condition
          const paramIndex = parseInt(placeholders[0][1]) - 1;
          const value = params[paramIndex];
          
          // Handle column = $N (extract column name, handling table aliases)
          const colMatch = condition.match(/(\w+)\.?(\w+)?\s*[=<>]+/);
          if (colMatch) {
            let colName = colMatch[2] || colMatch[1]; // Use second group if table alias present
            
            // Handle specific column types
            if (condition.includes('>=') || condition.includes('<=')) {
              if (condition.includes('importance')) {
                rows = rows.filter(r => r.importance >= value);
              }
            } else if (condition.includes('=')) {
              if (colName === 'id' && !condition.includes('agent_id') && !condition.includes('job_id')) {
                rows = rows.filter(r => r.id === value);
              } else if (colName === 'agent_id' || condition.includes('agent_id')) {
                rows = rows.filter(r => r.agent_id === value);
              } else if (colName === 'to_agent' || condition.includes('to_agent')) {
                rows = rows.filter(r => r.to_agent === value);
              } else if (colName === 'from_agent' || condition.includes('from_agent')) {
                rows = rows.filter(r => r.from_agent === value);
              } else if (colName === 'job_id' || condition.includes('job_id')) {
                rows = rows.filter(r => r.job_id === value);
              } else if (colName === 'memory_type' || condition.includes('memory_type')) {
                rows = rows.filter(r => r.memory_type === value);
              } else if (colName === 'status' && !condition.includes('in')) {
                rows = rows.filter(r => r.status === value);
              }
            }
          }
          
          // Handle IS NULL
          if (condition.includes('is null')) {
            if (condition.includes('read_at')) {
              rows = rows.filter(r => r.read_at === null);
            }
          }
        });
        
        // Handle IN clause (status IN ('a', 'b'))
        if (fullCondition.includes(' in ')) {
          const inMatch = fullCondition.match(/(\w+)\s+in\s*\(([^)]+)\)/i);
          if (inMatch) {
            const colName = inMatch[1];
            const values = inMatch[2].replace(/'/g, '').split(',').map(s => s.trim());
            rows = rows.filter(r => values.includes(r[colName]));
          }
        }
      }
    }
    
    // Handle ORDER BY
    if (text.toLowerCase().includes('order by')) {
      const orderMatch = text.match(/order\s+by\s+(?:\w+\.)?(\w+)(?:\s+(asc|desc))?/i);
      if (orderMatch) {
        const col = orderMatch[1];
        const dir = (orderMatch[2] || 'asc').toLowerCase();
        rows.sort((a, b) => {
          const aVal = a[col];
          const bVal = b[col];
          if (aVal < bVal) return dir === 'asc' ? -1 : 1;
          if (aVal > bVal) return dir === 'asc' ? 1 : -1;
          return 0;
        });
      }
    }
    
    // Handle LIMIT
    if (text.toLowerCase().includes('limit')) {
      const limitMatch = text.match(/limit\s+\$(\d+)/i);
      if (limitMatch) {
        const limitIndex = parseInt(limitMatch[1]) - 1;
        const limit = params[limitIndex];
        rows = rows.slice(0, limit);
      }
    }
    
    return { rows };
  }

  handleInsert(text, params) {
    const tableMatch = text.match(/into\s+(\w+)/i);
    if (!tableMatch) return { rows: [] };
    
    const tableName = tableMatch[1];
    
    // Parse column names
    const colMatch = text.match(/\(([^)]+)\)\s+values/i);
    if (!colMatch) return { rows: [] };
    
    const columns = colMatch[1].split(',').map(c => c.trim());
    
    const row = { id: this.generateId() };
    columns.forEach((col, idx) => {
      row[col] = params[idx] !== undefined ? params[idx] : null;
    });
    
    // Add timestamps
    if (!row.created_at) row.created_at = new Date().toISOString();
    if (!row.updated_at) row.updated_at = new Date().toISOString();
    
    this.tables[tableName].push(row);
    return { rows: [row] };
  }

  handleUpdate(text, params) {
    const tableMatch = text.match(/update\s+(\w+)/i);
    if (!tableMatch) return { rows: [] };
    
    const tableName = tableMatch[1];
    
    // Find WHERE condition
    const whereMatch = text.match(/where\s+(\w+)\s*=\s*\$(\d+)/i);
    if (!whereMatch) return { rows: [] };
    
    const whereCol = whereMatch[1];
    const whereParamIdx = parseInt(whereMatch[2]) - 1;
    const whereValue = params[whereParamIdx];
    
    // Find SET clause
    const setMatch = text.match(/set\s+(.+)\s+where/i);
    if (!setMatch) return { rows: [] };
    
    const setClause = setMatch[1];
    
    // Find rows to update
    const rowIndex = this.tables[tableName].findIndex(r => r[whereCol] === whereValue);
    if (rowIndex === -1) return { rows: [] };
    
    const row = this.tables[tableName][rowIndex];
    
    // Apply updates based on SET clause
    // Handle status = $2
    const statusMatch = setClause.match(/status\s*=\s*\$(\d+)/i);
    if (statusMatch) {
      row.status = params[parseInt(statusMatch[1]) - 1];
    }
    
    // Handle socket_id = $3
    const socketMatch = setClause.match(/socket_id\s*=\s*\$(\d+)/i);
    if (socketMatch) {
      row.socket_id = params[parseInt(socketMatch[1]) - 1];
    }
    
    // Handle updated_at
    row.updated_at = new Date().toISOString();
    
    return { rows: [row] };
  }

  handleDelete(text, params) {
    const tableMatch = text.match(/from\s+(\w+)/i);
    if (!tableMatch) return { rows: [] };
    
    const tableName = tableMatch[1];
    
    const whereMatch = text.match(/where\s+(\w+)\s*=\s*\$(\d+)/i);
    if (!whereMatch) return { rows: [] };
    
    const whereCol = whereMatch[1];
    const whereParamIdx = parseInt(whereMatch[2]) - 1;
    const whereValue = params[whereParamIdx];
    
    this.tables[tableName] = this.tables[tableName].filter(r => r[whereCol] !== whereValue);
    return { rows: [] };
  }

  // Transaction helper (simplified)
  async transaction(callback) {
    return await callback(this);
  }
}

const db = new InMemoryDB();

module.exports = {
  pool: {
    query: (text, params) => db.query(text, params),
    connect: async () => ({
      query: (text, params) => db.query(text, params),
      release: () => {},
      querySync: (text, params) => db.query(text, params)
    })
  },
  query: (text, params) => db.query(text, params),
  transaction: (callback) => db.transaction(callback)
};