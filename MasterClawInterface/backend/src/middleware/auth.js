const jwt = require('jsonwebtoken');
const config = require('../config/config');
const { logger } = require('./logger');

const authenticate = (req, res, next) => {
  const authHeader = req.headers.authorization;
  
  if (!authHeader) {
    return res.status(401).json({ error: 'No token provided' });
  }
  
  const parts = authHeader.split(' ');
  
  if (parts.length !== 2 || parts[0] !== 'Bearer') {
    return res.status(401).json({ error: 'Invalid token format' });
  }
  
  const token = parts[1];
  
  try {
    const decoded = jwt.verify(token, config.jwt.secret);
    req.user = decoded;
    next();
  } catch (error) {
    logger.warn('Invalid token:', error.message);
    return res.status(401).json({ error: 'Invalid token' });
  }
};

const optionalAuth = (req, res, next) => {
  const authHeader = req.headers.authorization;
  
  if (authHeader) {
    const parts = authHeader.split(' ');
    if (parts.length === 2 && parts[0] === 'Bearer') {
      try {
        const decoded = jwt.verify(parts[1], config.jwt.secret);
        req.user = decoded;
      } catch (error) {
        // Continue without auth
      }
    }
  }
  
  next();
};

module.exports = { authenticate, optionalAuth };
