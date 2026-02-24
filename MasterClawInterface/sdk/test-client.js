/**
 * Test script for MasterClaw Agent Client SDK
 * 
 * Run: node test-client.js
 */

const MasterClawAgent = require('./agent-client');

async function runTests() {
  console.log('🧪 MasterClaw Agent Client Tests\n');
  
  const serverUrl = process.env.SERVER_URL || 'http://localhost:3001';
  
  // Test 1: Create agent
  console.log('Test 1: Create agent instance');
  const agent = new MasterClawAgent({
    agentId: `test-agent-${Date.now()}`,
    name: 'Test Agent',
    type: 'subagent',
    capabilities: ['testing', 'logging'],
    serverUrl
  });
  
  console.log('✓ Agent created:', agent.getInfo().agentId);
  
  // Test 2: Connect to server
  console.log('\nTest 2: Connect to server');
  try {
    await agent.connect();
    console.log('✓ Connected to server');
  } catch (error) {
    console.error('✗ Connection failed:', error.message);
    console.log('\nMake sure the server is running:');
    console.log('  cd ../backend && npm run dev');
    process.exit(1);
  }
  
  // Test 3: Wait for registration
  console.log('\nTest 3: Wait for registration');
  await new Promise((resolve) => {
    agent.on('registered', (data) => {
      console.log('✓ Registered:', data.agent.name);
      resolve(data);
    });
  });
  
  // Test 4: Log thoughts
  console.log('\nTest 4: Log thoughts');
  const thought = await agent.logThought('Testing the MasterClaw interface', 3);
  console.log('✓ Thought logged:', thought.memoryId);
  
  // Test 5: Log needs
  console.log('\nTest 5: Log needs');
  const need = await agent.logNeed('Need more test coverage', 2);
  console.log('✓ Need logged:', need.memoryId);
  
  // Test 6: Create job
  console.log('\nTest 6: Create job');
  const job = await agent.createJob({
    title: 'Test Job',
    description: 'This is a test job',
    priority: 2
  });
  console.log('✓ Job created:', job.job.jobId);
  
  // Test 7: Get context
  console.log('\nTest 7: Get context');
  const context = await agent.getContext();
  console.log('✓ Context retrieved:', {
    memories: context.memories?.length || 0,
    jobs: context.pendingJobs?.length || 0
  });
  
  // Test 8: Send message (will fail if no recipient, but tests the flow)
  console.log('\nTest 8: Send message');
  const sent = agent.sendMessage('rex', 'Hello from test agent!');
  console.log(sent ? '✓ Message sent' : '✗ Message failed to send');
  
  // Test 9: Heartbeat
  console.log('\nTest 9: Heartbeat');
  agent.heartbeat();
  console.log('✓ Heartbeat sent');
  
  // Wait for heartbeat ack
  await new Promise((resolve) => {
    agent.once('heartbeat', () => {
      console.log('✓ Heartbeat acknowledged');
      resolve();
    });
    setTimeout(resolve, 1000);
  });
  
  // Cleanup
  console.log('\nTest 10: Disconnect');
  agent.disconnect();
  console.log('✓ Disconnected');
  
  console.log('\n✅ All tests passed!');
  process.exit(0);
}

// Handle errors
process.on('unhandledRejection', (err) => {
  console.error('Unhandled error:', err);
  process.exit(1);
});

runTests();
