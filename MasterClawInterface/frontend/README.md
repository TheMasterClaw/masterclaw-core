# MasterClaw Chat Interface

Real-time chat interface for Rex to communicate with AI agents.

## Features

- **Agent Registry**: View all connected agents with status
- **Real-time Messaging**: WebSocket-based instant messaging
- **Agent Memory Panel**: View agent thoughts, jobs, and needs
- **Command Interface**: Send commands to agents
- **Message Threading**: Persistent conversation history per agent

## Tech Stack

- React 18 + TypeScript
- Tailwind CSS
- Socket.io-client
- Vite

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

## Environment Variables

```
VITE_SOCKET_URL=ws://localhost:3001
```

## WebSocket Events

### Client → Server
- `message:send` - Send message to agent
- `message:broadcast` - Broadcast to all agents
- `agents:list` - Request agent list
- `agent:memory` - Request agent memory
- `agent:command` - Send command to agent

### Server → Client
- `message` - Incoming message
- `agent:update` - Agent state update
- `agent:status` - Agent status change
