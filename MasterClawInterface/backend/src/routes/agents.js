const express = require('express');
const router = express.Router();
const { Agent, Message, AgentMemory, AgentJob } = require('../models');
const { logger } = require('../middleware/logger');

// Get all agents
router.get('/', async (req, res) => {
  try {
    const { status, type, limit, offset } = req.query;
    const agents = await Agent.findAll({ status, type, limit, offset });
    res.json({ agents });
  } catch (error) {
    logger.error('Error fetching agents:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get agent by ID
router.get('/:agentId', async (req, res) => {
  try {
    const agent = await Agent.findByAgentId(req.params.agentId);
    if (!agent) {
      return res.status(404).json({ error: 'Agent not found' });
    }
    res.json({ agent });
  } catch (error) {
    logger.error('Error fetching agent:', error);
    res.status(500).json({ error: error.message });
  }
});

// Register new agent
router.post('/', async (req, res) => {
  try {
    const { agentId, name, type, capabilities, metadata } = req.body;
    
    if (!agentId) {
      return res.status(400).json({ error: 'agentId is required' });
    }
    
    // Check if agent already exists
    const existing = await Agent.findByAgentId(agentId);
    if (existing) {
      return res.status(409).json({ error: 'Agent already exists', agent: existing });
    }
    
    const agent = await Agent.create({
      agentId,
      name: name || agentId,
      type: type || 'subagent',
      capabilities: capabilities || [],
      metadata: metadata || {}
    });
    
    res.status(201).json({ success: true, agent });
  } catch (error) {
    logger.error('Error creating agent:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update agent
router.put('/:agentId', async (req, res) => {
  try {
    const updates = req.body;
    const agent = await Agent.update(req.params.agentId, updates);
    
    if (!agent) {
      return res.status(404).json({ error: 'Agent not found' });
    }
    
    res.json({ success: true, agent });
  } catch (error) {
    logger.error('Error updating agent:', error);
    res.status(500).json({ error: error.message });
  }
});

// Delete agent
router.delete('/:agentId', async (req, res) => {
  try {
    await Agent.delete(req.params.agentId);
    res.json({ success: true, message: 'Agent deleted' });
  } catch (error) {
    logger.error('Error deleting agent:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get agent stats
router.get('/:agentId/stats', async (req, res) => {
  try {
    const memoryStats = await AgentMemory.getStats(req.params.agentId);
    const jobStats = await AgentJob.findForAgent(req.params.agentId);
    
    res.json({
      agentId: req.params.agentId,
      memory: memoryStats,
      jobs: {
        total: jobStats.length,
        pending: jobStats.filter(j => j.status === 'pending').length,
        inProgress: jobStats.filter(j => j.status === 'in_progress').length,
        completed: jobStats.filter(j => j.status === 'completed').length
      }
    });
  } catch (error) {
    logger.error('Error fetching agent stats:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get agent memory
router.get('/:agentId/memory', async (req, res) => {
  try {
    const { types, limit, minImportance } = req.query;
    const memories = await AgentMemory.getForAgent(req.params.agentId, {
      types: types ? types.split(',') : [],
      limit: parseInt(limit) || 50,
      minImportance: parseInt(minImportance) || 1
    });
    res.json({ memories });
  } catch (error) {
    logger.error('Error fetching agent memory:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get agent needs
router.get('/:agentId/needs', async (req, res) => {
  try {
    const needs = await AgentMemory.getNeeds(req.params.agentId);
    res.json({ needs });
  } catch (error) {
    logger.error('Error fetching agent needs:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get agent jobs
router.get('/:agentId/jobs', async (req, res) => {
  try {
    const { status, limit } = req.query;
    const jobs = await AgentJob.findForAgent(req.params.agentId, { status, limit });
    res.json({ jobs });
  } catch (error) {
    logger.error('Error fetching agent jobs:', error);
    res.status(500).json({ error: error.message });
  }
});

// Create a job for an agent
router.post('/:agentId/jobs', async (req, res) => {
  try {
    const { title, description, priority = 2, assignedBy } = req.body;
    
    if (!title) {
      return res.status(400).json({ error: 'title is required' });
    }
    
    const job = await AgentJob.create({
      agentId: req.params.agentId,
      title,
      description,
      priority,
      assignedBy
    });
    
    // Notify via WebSocket if server is available
    if (global.wsServer) {
      global.wsServer.broadcastToAgent(req.params.agentId, 'new_job', {
        jobId: job.job_id,
        title,
        description,
        priority,
        assignedBy
      });
    }
    
    res.status(201).json({ success: true, job });
  } catch (error) {
    logger.error('Error creating job:', error);
    res.status(500).json({ error: error.message });
  }
});

// Log memory (thought, desire, blocker) for an agent
router.post('/:agentId/memory', async (req, res) => {
  try {
    const { memoryType, content, context = {}, importance = 1 } = req.body;
    
    if (!memoryType || !content) {
      return res.status(400).json({ error: 'memoryType and content are required' });
    }
    
    const memory = await AgentMemory.log({
      agentId: req.params.agentId,
      memoryType,
      content,
      context,
      importance
    });
    
    // Notify via WebSocket if high importance need/blocker
    if (global.wsServer && (memoryType === 'need' || memoryType === 'blocker') && importance >= 4) {
      global.wsServer.broadcastToAll('agent_alert', {
        agentId: req.params.agentId,
        type: memoryType,
        content,
        importance,
        memoryId: memory.id
      });
    }
    
    res.status(201).json({ success: true, memory });
  } catch (error) {
    logger.error('Error logging memory:', error);
    res.status(500).json({ error: error.message });
  }
});

// Update job status
router.put('/:agentId/jobs/:jobId', async (req, res) => {
  try {
    const { status, result } = req.body;
    
    if (!status) {
      return res.status(400).json({ error: 'status is required' });
    }
    
    const job = await AgentJob.updateStatus(req.params.jobId, status, result);
    
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }
    
    res.json({ success: true, job });
  } catch (error) {
    logger.error('Error updating job:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get agent desires (memory type = 'need')
router.get('/:agentId/desires', async (req, res) => {
  try {
    const { unmetOnly = true } = req.query;
    const desires = await AgentMemory.getForAgent(req.params.agentId, {
      types: ['need'],
      limit: 50
    });
    res.json({ desires });
  } catch (error) {
    logger.error('Error fetching agent desires:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get agent blockers (memory type = 'blocker' - stored as memory with specific pattern)
router.get('/:agentId/blockers', async (req, res) => {
  try {
    const blockers = await AgentMemory.getForAgent(req.params.agentId, {
      types: ['observation'],  // Using observation for blockers or we can filter by content
      limit: 50
    });
    // Filter for blocker-related observations
    const filtered = blockers.filter(b => 
      b.content.toLowerCase().includes('block') || 
      b.content.toLowerCase().includes('stuck') ||
      b.context?.type === 'blocker'
    );
    res.json({ blockers: filtered });
  } catch (error) {
    logger.error('Error fetching agent blockers:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
