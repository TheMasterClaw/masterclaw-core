const request = require('supertest');
const { startServer } = require('../src/server');

describe('MasterClaw Chat Server', () => {
  let server;
  let app;
  
  beforeAll(async () => {
    process.env.NODE_ENV = 'test';
    server = await startServer();
    // Get Express app from server
    app = server;
  });
  
  afterAll((done) => {
    server.close(done);
  });
  
  describe('Health Endpoint', () => {
    it('should return 200 and status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('ok');
      expect(res.body.service).toBe('masterclaw-chat');
    });
  });
  
  describe('Agents API', () => {
    it('should create a new agent', async () => {
      const res = await request(app)
        .post('/api/agents')
        .send({
          agentId: 'test-agent-1',
          name: 'Test Agent',
          type: 'subagent'
        });
      
      expect(res.status).toBe(201);
      expect(res.body.success).toBe(true);
      expect(res.body.agent.agent_id).toBe('test-agent-1');
    });
    
    it('should get agent by ID', async () => {
      const res = await request(app).get('/api/agents/test-agent-1');
      expect(res.status).toBe(200);
      expect(res.body.agent.agent_id).toBe('test-agent-1');
    });
    
    it('should list all agents', async () => {
      const res = await request(app).get('/api/agents');
      expect(res.status).toBe(200);
      expect(Array.isArray(res.body.agents)).toBe(true);
    });
  });
  
  describe('Messages API', () => {
    it('should create a message via REST', async () => {
      const res = await request(app)
        .post('/api/messages')
        .send({
          fromAgent: 'test-agent-1',
          toAgent: 'test-agent-2',
          content: 'Hello from test!',
          type: 'text'
        });
      
      expect(res.status).toBe(201);
      expect(res.body.success).toBe(true);
      expect(res.body.message.content).toBe('Hello from test!');
    });
  });
});
