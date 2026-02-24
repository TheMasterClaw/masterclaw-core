const express = require('express');
const router = express.Router();
const { Message } = require('../models');
const { logger } = require('../middleware/logger');

// Get message history between two agents
router.get('/conversation/:agent1/:agent2', async (req, res) => {
  try {
    const { limit, offset } = req.query;
    const messages = await Message.findBetweenAgents(
      req.params.agent1,
      req.params.agent2,
      { limit: parseInt(limit) || 50, offset: parseInt(offset) || 0 }
    );
    res.json({ messages });
  } catch (error) {
    logger.error('Error fetching conversation:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get messages for an agent
router.get('/agent/:agentId', async (req, res) => {
  try {
    const { limit, offset, unreadOnly } = req.query;
    const messages = await Message.findForAgent(req.params.agentId, {
      limit: parseInt(limit) || 50,
      offset: parseInt(offset) || 0,
      unreadOnly: unreadOnly === 'true'
    });
    res.json({ messages });
  } catch (error) {
    logger.error('Error fetching messages:', error);
    res.status(500).json({ error: error.message });
  }
});

// Send message via REST (fallback when WebSocket unavailable)
router.post('/', async (req, res) => {
  try {
    const { fromAgent, toAgent, content, type, metadata } = req.body;
    
    if (!fromAgent || !toAgent || !content) {
      return res.status(400).json({ error: 'fromAgent, toAgent, and content are required' });
    }
    
    const message = await Message.create({
      fromAgent,
      toAgent,
      content,
      type: type || 'text',
      metadata: metadata || {}
    });
    
    res.status(201).json({ success: true, message });
  } catch (error) {
    logger.error('Error creating message:', error);
    res.status(500).json({ error: error.message });
  }
});

// Mark message as read
router.put('/:messageId/read', async (req, res) => {
  try {
    const message = await Message.markAsRead(req.params.messageId);
    res.json({ success: true, message });
  } catch (error) {
    logger.error('Error marking message as read:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get unread count for agent
router.get('/agent/:agentId/unread', async (req, res) => {
  try {
    const count = await Message.getUnreadCount(req.params.agentId);
    res.json({ agentId: req.params.agentId, unreadCount: count });
  } catch (error) {
    logger.error('Error fetching unread count:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
