# RHCP Chatbot Usage Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [API Usage](#api-usage)
6. [Integration Examples](#integration-examples)
7. [Advanced Usage](#advanced-usage)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Getting Started

The RHCP Chatbot is a specialized conversational AI system designed for Red Hot Chili Peppers fans. It provides information about the band's history, members, albums, and songs through natural language interactions.

### Prerequisites

**For Node.js Version:**
- Node.js >= 14.0.0
- npm or yarn package manager

**For Python Version:**
- Python >= 3.7
- pip package manager

---

## Installation

### Node.js Setup

1. **Clone the repository:**
```bash
git clone https://github.com/gilbertordx/rhcp-chatbot.git
cd rhcp-chatbot
```

2. **Install dependencies:**
```bash
npm install
```

3. **Create environment file:**
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
NODE_ENV=development
PORT=3000
```

### Python Setup

1. **Navigate to Python directory:**
```bash
cd rhcp-chatbot-py
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Download NLTK data:**
```python
python -c "import nltk; nltk.download('punkt')"
```

---

## Configuration

### Environment Variables

**Node.js:**
```env
NODE_ENV=development          # Environment mode
PORT=3000                    # Server port
```

**Python:**
```env
PORT=3000                    # Server port
```

### Confidence Thresholds

The chatbot uses confidence thresholds to determine intent recognition quality:

- **Node.js**: `CONFIDENCE_THRESHOLD = 0.0005` (in `src/chatbotProcessor.js`)
- **Python**: `CONFIDENCE_THRESHOLD = 0.5` (in `rhcp-chatbot-py/app/chatbot/processor.py`)

Lower values are more permissive, higher values are more strict.

---

## Running the Application

### Node.js Version

**Development mode:**
```bash
npm run dev
```

**Production mode:**
```bash
npm start
```

**Run tests:**
```bash
npm test
```

### Python Version

**Development mode:**
```bash
cd rhcp-chatbot-py
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

**Production mode:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

### Docker

**Build and run:**
```bash
# Node.js version
docker build -t rhcp-chatbot .
docker run -p 3000:3000 rhcp-chatbot

# Python version
cd rhcp-chatbot-py
docker build -t rhcp-chatbot-py .
docker run -p 3000:3000 rhcp-chatbot-py
```

---

## API Usage

### Basic Chat Interaction

**cURL Example:**
```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about Anthony Kiedis"}'
```

**Response:**
```json
{
  "message": "Anthony Kiedis: Anthony Kiedis is the lead vocalist and primary lyricist of RHCP. He has been with the band since its inception in 1983.",
  "intent": "member.biography",
  "confidence": 0.92,
  "entities": [
    {
      "type": "member",
      "value": {
        "name": "Anthony Kiedis",
        "role": "Lead Vocals",
        "memberSince": 1983,
        "biography": "..."
      }
    }
  ]
}
```

### Health Check

**Node.js:**
```bash
curl http://localhost:3000/
```

**Python:**
```bash
curl http://localhost:3000/
```

---

## Integration Examples

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

class RHCPChatbotClient {
  constructor(baseURL = 'http://localhost:3000') {
    this.baseURL = baseURL;
  }

  async chat(message) {
    try {
      const response = await axios.post(`${this.baseURL}/api/chat`, {
        message: message
      });
      return response.data;
    } catch (error) {
      console.error('Chat error:', error.response?.data || error.message);
      throw error;
    }
  }

  async getHealthStatus() {
    try {
      const response = await axios.get(`${this.baseURL}/`);
      return response.data;
    } catch (error) {
      console.error('Health check error:', error.message);
      throw error;
    }
  }
}

// Usage
async function example() {
  const client = new RHCPChatbotClient();
  
  // Check if service is running
  const health = await client.getHealthStatus();
  console.log('Service status:', health);
  
  // Chat examples
  const responses = await Promise.all([
    client.chat("Who is the bassist of RHCP?"),
    client.chat("What albums has the band released?"),
    client.chat("Tell me about Blood Sugar Sex Magik"),
    client.chat("What songs are on Californication?")
  ]);
  
  responses.forEach((response, index) => {
    console.log(`Response ${index + 1}:`, response.message);
    console.log(`Intent: ${response.intent}, Confidence: ${response.confidence}`);
    console.log('---');
  });
}

example();
```

### Python Client

```python
import asyncio
import aiohttp
import json

class RHCPChatbotClient:
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
    
    async def chat(self, message):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/api/chat/",
                    json={"message": message}
                ) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Chat error: {e}")
                raise
    
    async def get_health_status(self):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/") as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Health check error: {e}")
                raise

async def example():
    client = RHCPChatbotClient()
    
    # Check service health
    health = await client.get_health_status()
    print(f"Service status: {health}")
    
    # Chat examples
    messages = [
        "Who are the current members of RHCP?",
        "What is John Frusciante known for?",
        "Tell me about the album Stadium Arcadium",
        "What year was the band formed?"
    ]
    
    for message in messages:
        response = await client.chat(message)
        print(f"Q: {message}")
        print(f"A: {response['message']}")
        print(f"Intent: {response['intent']}, Confidence: {response['confidence']:.2f}")
        print("---")

# Run the example
asyncio.run(example())
```

### React Frontend Integration

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Check if chatbot service is available
    checkConnection();
  }, []);

  const checkConnection = async () => {
    try {
      await axios.get('http://localhost:3000/');
      setIsConnected(true);
    } catch (error) {
      setIsConnected(false);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = inputMessage;
    setInputMessage('');
    setIsLoading(true);

    // Add user message to chat
    setMessages(prev => [...prev, {
      type: 'user',
      content: userMessage,
      timestamp: new Date()
    }]);

    try {
      const response = await axios.post('http://localhost:3000/api/chat', {
        message: userMessage
      });

      // Add bot response to chat
      setMessages(prev => [...prev, {
        type: 'bot',
        content: response.data.message,
        intent: response.data.intent,
        confidence: response.data.confidence,
        entities: response.data.entities,
        timestamp: new Date()
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'error',
        content: 'Sorry, I encountered an error processing your message.',
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-interface">
      <div className="connection-status">
        Status: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
      </div>
      
      <div className="messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.type}`}>
            <div className="content">{msg.content}</div>
            {msg.intent && (
              <div className="metadata">
                Intent: {msg.intent} | Confidence: {(msg.confidence * 100).toFixed(1)}%
              </div>
            )}
          </div>
        ))}
        {isLoading && <div className="message loading">Thinking...</div>}
      </div>
      
      <div className="input-area">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask me about Red Hot Chili Peppers..."
          disabled={!isConnected}
        />
        <button onClick={sendMessage} disabled={!isConnected || isLoading}>
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatInterface;
```

---

## Advanced Usage

### Custom Intent Recognition

You can extend the chatbot's understanding by modifying the training data:

**Adding new intents in `src/data/training/rhcp-corpus.json`:**
```json
{
  "data": [
    {
      "intent": "tour.dates",
      "utterances": [
        "When is the next tour?",
        "Are they touring this year?",
        "What are the tour dates?",
        "When can I see them live?"
      ],
      "answers": [
        "I don't have current tour information, but you can check their official website for the latest tour dates.",
        "Tour dates are typically announced on their official channels. Check rhcp.com for updates."
      ]
    }
  ]
}
```

### Entity Recognition Customization

Modify entity recognition in `ChatbotProcessor` to handle new entity types:

```javascript
// In src/chatbotProcessor.js
processMessage(message) {
  // ... existing code ...
  
  // Add custom entity recognition
  for (const venue of this.knownVenues) {
    if (cleanMessage.includes(venue.toLowerCase())) {
      entities.push({ 
        type: 'venue', 
        value: venue 
      });
    }
  }
  
  // ... rest of the method
}
```

### Confidence Threshold Tuning

Adjust confidence thresholds based on your requirements:

```javascript
// Lower threshold = more permissive (may catch more intents but with lower accuracy)
const CONFIDENCE_THRESHOLD = 0.3;

// Higher threshold = more strict (fewer false positives but may miss valid intents)
const CONFIDENCE_THRESHOLD = 0.8;
```

### Custom Response Generation

Implement custom response logic:

```javascript
// In ChatbotProcessor.processMessage()
if (intent === 'custom.intent' && entities.find(e => e.type === 'custom')) {
  const customEntity = entities.find(e => e.type === 'custom').value;
  responseMessage = generateCustomResponse(customEntity, message);
  handledBySpecificLogic = true;
}

function generateCustomResponse(entity, originalMessage) {
  // Custom logic here
  return `Custom response for ${entity.name}`;
}
```

---

## Troubleshooting

### Common Issues

#### 1. "Chatbot processor is not initialized"

**Cause**: The chatbot initialization failed or is still in progress.

**Solutions**:
- Check that all training data files exist in `src/data/`
- Verify NLTK data is downloaded (Python version)
- Check server logs for initialization errors
- Wait for initialization to complete (may take 30+ seconds on first run)

#### 2. Low confidence scores

**Cause**: User input doesn't match training data patterns well.

**Solutions**:
- Add more training examples for similar intents
- Lower the confidence threshold temporarily
- Check for typos in user input
- Add more diverse utterances to training data

#### 3. "Module not found" errors

**Node.js Solutions**:
```bash
rm -rf node_modules package-lock.json
npm install
```

**Python Solutions**:
```bash
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt')"
```

#### 4. Port already in use

**Solutions**:
```bash
# Find process using port 3000
lsof -i :3000

# Kill the process
kill -9 <PID>

# Or use different port
PORT=3001 npm start
```

#### 5. Memory issues during training

**Solutions**:
- Reduce training data size
- Increase Node.js memory limit: `node --max-old-space-size=4096 src/app.js`
- Use Python version for better memory management

### Debug Mode

Enable debug logging:

**Node.js:**
```bash
NODE_ENV=development npm run dev
```

**Python:**
```bash
uvicorn app.main:app --log-level debug --reload
```

### Performance Monitoring

Monitor response times and accuracy:

```javascript
// Add timing to your client
const startTime = Date.now();
const response = await client.chat(message);
const responseTime = Date.now() - startTime;

console.log(`Response time: ${responseTime}ms`);
console.log(`Confidence: ${response.confidence}`);
```

---

## Best Practices

### 1. Input Validation

Always validate user input:

```javascript
function validateMessage(message) {
  if (!message || typeof message !== 'string') {
    throw new Error('Message must be a non-empty string');
  }
  
  if (message.length > 1000) {
    throw new Error('Message too long');
  }
  
  return message.trim();
}
```

### 2. Error Handling

Implement comprehensive error handling:

```javascript
async function safeChat(message) {
  try {
    const validMessage = validateMessage(message);
    const response = await client.chat(validMessage);
    return response;
  } catch (error) {
    if (error.response?.status === 400) {
      return { error: 'Invalid message format' };
    } else if (error.response?.status === 503) {
      return { error: 'Service temporarily unavailable' };
    } else {
      return { error: 'An unexpected error occurred' };
    }
  }
}
```

### 3. Rate Limiting

Implement client-side rate limiting:

```javascript
class RateLimitedClient {
  constructor(maxRequestsPerMinute = 60) {
    this.requests = [];
    this.maxRequests = maxRequestsPerMinute;
  }
  
  async chat(message) {
    await this.checkRateLimit();
    // ... make request
  }
  
  async checkRateLimit() {
    const now = Date.now();
    this.requests = this.requests.filter(time => now - time < 60000);
    
    if (this.requests.length >= this.maxRequests) {
      const waitTime = 60000 - (now - this.requests[0]);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    this.requests.push(now);
  }
}
```

### 4. Caching

Cache responses for common queries:

```javascript
class CachedChatClient {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
  }
  
  async chat(message) {
    const cacheKey = message.toLowerCase();
    const cached = this.cache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.response;
    }
    
    const response = await this.makeRequest(message);
    this.cache.set(cacheKey, {
      response,
      timestamp: Date.now()
    });
    
    return response;
  }
}
```

### 5. Monitoring and Analytics

Track usage patterns:

```javascript
class AnalyticsClient {
  constructor() {
    this.metrics = {
      totalRequests: 0,
      intentCounts: {},
      averageConfidence: 0,
      errorRate: 0
    };
  }
  
  async chat(message) {
    this.metrics.totalRequests++;
    
    try {
      const response = await this.makeRequest(message);
      
      // Track intent usage
      this.metrics.intentCounts[response.intent] = 
        (this.metrics.intentCounts[response.intent] || 0) + 1;
      
      // Track confidence
      this.updateAverageConfidence(response.confidence);
      
      return response;
    } catch (error) {
      this.metrics.errorRate = this.calculateErrorRate();
      throw error;
    }
  }
  
  getAnalytics() {
    return this.metrics;
  }
}
```

### 6. Testing

Write comprehensive tests:

```javascript
// Test example
describe('RHCP Chatbot', () => {
  test('should recognize member biography requests', async () => {
    const response = await client.chat('Tell me about Anthony Kiedis');
    
    expect(response.intent).toBe('member.biography');
    expect(response.confidence).toBeGreaterThan(0.7);
    expect(response.entities).toHaveLength(1);
    expect(response.entities[0].type).toBe('member');
    expect(response.entities[0].value.name).toBe('Anthony Kiedis');
  });
  
  test('should handle unrecognized input gracefully', async () => {
    const response = await client.chat('asdfghjkl');
    
    expect(response.intent).toBe('unrecognized');
    expect(response.message).toContain("didn't understand");
  });
});
```

This completes the comprehensive usage guide for the RHCP Chatbot system. The guide covers installation, configuration, API usage, integration examples, advanced features, troubleshooting, and best practices to help users effectively utilize the chatbot system.