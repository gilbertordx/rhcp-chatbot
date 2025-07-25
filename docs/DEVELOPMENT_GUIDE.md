# RHCP Chatbot Development Guide

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Coding Standards](#coding-standards)
6. [Testing](#testing)
7. [Data Management](#data-management)
8. [Machine Learning Pipeline](#machine-learning-pipeline)
9. [Deployment](#deployment)
10. [Contributing](#contributing)

---

## Architecture Overview

The RHCP Chatbot system consists of two main implementations:

### Node.js Implementation (Primary)
- **Framework**: Express.js
- **NLP Library**: Natural.js (BayesClassifier/LogisticRegressionClassifier)
- **Data Storage**: JSON files for training data and static content
- **Architecture**: MVC pattern with separation of concerns

### Python Implementation (Alternative)
- **Framework**: FastAPI
- **ML Library**: scikit-learn with TF-IDF vectorization
- **Data Storage**: JSON files with joblib model persistence
- **Architecture**: Clean architecture with service layers

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   HTTP Layer    │    │  Processing      │    │   Data Layer    │
│                 │    │                  │    │                 │
│ • Routes        │───▶│ • ChatProcessor  │───▶│ • Training Data │
│ • Controllers   │    │ • NLU Classifier │    │ • Static Data   │
│ • Middleware    │    │ • Entity Extract │    │ • Models        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Data Flow

1. **User Input** → HTTP Request
2. **Route Handler** → Input validation
3. **Controller** → Message processing
4. **ChatbotProcessor** → Intent classification & entity extraction
5. **Response Generation** → Template-based responses
6. **HTTP Response** → Structured JSON response

---

## Development Setup

### Prerequisites

- **Node.js**: >= 14.0.0
- **Python**: >= 3.7 (for Python implementation)
- **Git**: Latest version
- **Code Editor**: VS Code recommended

### Initial Setup

1. **Clone and setup repository:**
```bash
git clone https://github.com/gilbertordx/rhcp-chatbot.git
cd rhcp-chatbot

# Install Node.js dependencies
npm install

# Setup Python environment (optional)
cd rhcp-chatbot-py
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt')"
```

2. **Environment configuration:**
```bash
# Create .env file
cp .env.example .env

# Edit .env with your settings
NODE_ENV=development
PORT=3000
```

3. **Verify setup:**
```bash
# Test Node.js version
npm run dev

# Test Python version (in rhcp-chatbot-py directory)
uvicorn app.main:app --reload
```

### Development Tools

**Recommended VS Code Extensions:**
- ESLint
- Prettier
- Python
- REST Client
- GitLens

**Package Scripts:**
```bash
npm run dev          # Development server with hot reload
npm run start        # Production server
npm run test         # Run test suite
npm run lint         # ESLint check
npm run format       # Prettier formatting
npm run seed         # Seed database (future feature)
```

---

## Project Structure

### Node.js Structure
```
src/
├── app.js                 # Main application entry point
├── initializer.js         # Chatbot initialization logic
├── chatbotProcessor.js    # Core processing engine
├── http/
│   ├── controllers/       # Request handlers
│   │   └── chatController.js
│   └── routes/           # Route definitions
│       └── chatRoutes.js
├── models/               # Data models (future)
├── data/
│   ├── static/           # Band info, discography
│   │   ├── band-info.json
│   │   └── discography.json
│   └── training/         # Training corpus
│       ├── base-corpus.json
│       └── rhcp-corpus.json
└── scripts/              # Utility scripts (future)
```

### Python Structure
```
rhcp-chatbot-py/
├── app/
│   ├── main.py           # FastAPI application
│   ├── api/
│   │   └── routes/
│   │       └── chat.py   # Chat endpoints
│   ├── chatbot/
│   │   ├── initializer.py # Chatbot setup
│   │   ├── processor.py   # Processing logic
│   │   └── data/         # Training/static data
│   ├── core/
│   │   └── config.py     # Configuration
│   ├── models/           # Data models (future)
│   └── services/         # Business logic (future)
├── tests/                # Test files
├── requirements.txt      # Python dependencies
└── Dockerfile           # Container configuration
```

---

## Development Workflow

### Git Workflow

1. **Create feature branch:**
```bash
git checkout -b feature/your-feature-name
```

2. **Make changes and commit:**
```bash
git add .
git commit -m "feat: Add new intent recognition for tour dates"
```

3. **Push and create PR:**
```bash
git push origin feature/your-feature-name
# Create pull request on GitHub
```

### Commit Message Format

Follow conventional commits:
```
type(scope): description

Types: feat, fix, docs, style, refactor, test, chore
Scope: component affected (optional)
```

Examples:
- `feat(processor): add venue entity recognition`
- `fix(api): handle empty message validation`
- `docs(readme): update installation instructions`
- `test(chatbot): add intent classification tests`

### Code Review Process

1. **Self-review checklist:**
   - [ ] Code follows style guidelines
   - [ ] Tests pass locally
   - [ ] Documentation updated
   - [ ] No console.log statements
   - [ ] Error handling implemented

2. **PR Requirements:**
   - Clear description of changes
   - Link to related issues
   - Screenshots for UI changes
   - Test coverage maintained

---

## Coding Standards

### JavaScript/Node.js

**ESLint Configuration:**
```javascript
// .eslintrc.js
module.exports = {
  extends: ['eslint:recommended', 'prettier'],
  env: {
    node: true,
    es2021: true,
    jest: true
  },
  rules: {
    'no-console': 'warn',
    'no-unused-vars': 'error',
    'prefer-const': 'error'
  }
};
```

**Code Style:**
```javascript
// Good
const ChatbotProcessor = require('./chatbotProcessor');

class ChatService {
  constructor(processor) {
    this.processor = processor;
  }

  async processMessage(message) {
    if (!message || typeof message !== 'string') {
      throw new Error('Invalid message format');
    }
    
    return await this.processor.processMessage(message.trim());
  }
}

// Avoid
var processor = require('./chatbotProcessor')
function processMessage(message) {
  return processor.processMessage(message)
}
```

### Python

**Style Guide**: PEP 8 compliance

```python
# Good
from typing import Dict, List, Optional
import logging

class ChatbotProcessor:
    """Processes chat messages and generates responses."""
    
    def __init__(self, classifier, training_data: Dict, static_data: Dict):
        self.classifier = classifier
        self.training_data = training_data
        self.static_data = static_data
        
    def process_message(self, message: str) -> Dict:
        """Process a user message and return response."""
        if not message or not isinstance(message, str):
            raise ValueError("Message must be a non-empty string")
            
        return self._generate_response(message.strip())
```

### Documentation Standards

**JSDoc for JavaScript:**
```javascript
/**
 * Processes a user chat message using the provided ChatbotProcessor.
 * @param {ChatbotProcessor} chatbotProcessor - The initialized processor instance.
 * @param {string} userMessage - The message from the user.
 * @returns {Promise<Object>} The chatbot's response.
 * @throws {Error} If processor is not initialized or message is invalid.
 */
async function processChatMessage(chatbotProcessor, userMessage) {
  // Implementation
}
```

**Python Docstrings:**
```python
def process_message(self, message: str) -> Dict:
    """
    Process a user message and return chatbot response.
    
    Args:
        message (str): The user's input message
        
    Returns:
        Dict: Response containing message, intent, confidence, and entities
        
    Raises:
        ValueError: If message is empty or invalid
    """
    pass
```

---

## Testing

### Test Structure

```
test/
├── unit/
│   ├── chatbotProcessor.test.js
│   ├── controllers/
│   └── routes/
├── integration/
│   └── api.test.js
└── fixtures/
    └── testData.json
```

### Unit Testing (Jest)

```javascript
// test/unit/chatbotProcessor.test.js
const ChatbotProcessor = require('../../src/chatbotProcessor');

describe('ChatbotProcessor', () => {
  let processor;
  let mockClassifier;
  let mockTrainingData;
  let mockStaticData;

  beforeEach(() => {
    mockClassifier = {
      getClassifications: jest.fn()
    };
    
    mockTrainingData = {
      base: { data: [] },
      rhcp: { data: [] }
    };
    
    mockStaticData = {
      bandInfo: {
        currentMembers: [
          { name: 'Anthony Kiedis', role: 'Lead Vocals' }
        ]
      }
    };
    
    processor = new ChatbotProcessor(
      mockClassifier, 
      mockTrainingData, 
      mockStaticData
    );
  });

  describe('processMessage', () => {
    test('should recognize member biography intent', async () => {
      mockClassifier.getClassifications.mockReturnValue([
        { label: 'member.biography', value: 0.9 }
      ]);

      const result = await processor.processMessage('Tell me about Anthony Kiedis');

      expect(result.intent).toBe('member.biography');
      expect(result.confidence).toBe(0.9);
      expect(result.entities).toHaveLength(1);
      expect(result.entities[0].type).toBe('member');
    });

    test('should handle unrecognized input', async () => {
      mockClassifier.getClassifications.mockReturnValue([
        { label: 'unknown', value: 0.1 }
      ]);

      const result = await processor.processMessage('asdfghjkl');

      expect(result.intent).toBe('unrecognized');
      expect(result.message).toContain("didn't understand");
    });
  });
});
```

### Integration Testing

```javascript
// test/integration/api.test.js
const request = require('supertest');
const app = require('../../src/app');

describe('Chat API', () => {
  test('POST /api/chat should process message', async () => {
    const response = await request(app)
      .post('/api/chat')
      .send({ message: 'Hello' })
      .expect(200);

    expect(response.body).toHaveProperty('message');
    expect(response.body).toHaveProperty('intent');
    expect(response.body).toHaveProperty('confidence');
  });

  test('POST /api/chat should return 400 for empty message', async () => {
    await request(app)
      .post('/api/chat')
      .send({ message: '' })
      .expect(400);
  });
});
```

### Python Testing (pytest)

```python
# tests/test_processor.py
import pytest
from app.chatbot.processor import ChatbotProcessor

class TestChatbotProcessor:
    @pytest.fixture
    def processor(self):
        mock_classifier = MockClassifier()
        training_data = {"base": {"data": []}, "rhcp": {"data": []}}
        static_data = {
            "bandInfo": {
                "currentMembers": [
                    {"name": "Anthony Kiedis", "role": "Lead Vocals"}
                ]
            }
        }
        return ChatbotProcessor(mock_classifier, training_data, static_data)

    def test_process_message_member_biography(self, processor):
        result = processor.process_message("Tell me about Anthony Kiedis")
        
        assert result["intent"] == "member.biography"
        assert result["confidence"] > 0.5
        assert len(result["entities"]) == 1
        assert result["entities"][0]["type"] == "member"
```

### Test Coverage

Maintain minimum 80% test coverage:
```bash
# Node.js
npm run test -- --coverage

# Python
pytest --cov=app --cov-report=html
```

---

## Data Management

### Training Data Format

```json
{
  "data": [
    {
      "intent": "member.biography",
      "utterances": [
        "Tell me about {member}",
        "Who is {member}?",
        "What do you know about {member}?"
      ],
      "answers": [
        "Here's information about {member}...",
        "{member} is known for..."
      ]
    }
  ]
}
```

### Static Data Management

**Band Information Schema:**
```json
{
  "name": "Red Hot Chili Peppers",
  "formed": 1983,
  "currentMembers": [
    {
      "name": "string",
      "role": "string",
      "memberSince": "number",
      "birthDate": "YYYY-MM-DD",
      "biography": "string"
    }
  ]
}
```

### Data Validation

```javascript
// src/utils/dataValidator.js
const Joi = require('joi');

const memberSchema = Joi.object({
  name: Joi.string().required(),
  role: Joi.string().required(),
  memberSince: Joi.number().integer().min(1980),
  biography: Joi.string().required()
});

function validateBandInfo(data) {
  const schema = Joi.object({
    name: Joi.string().required(),
    formed: Joi.number().integer().min(1980),
    currentMembers: Joi.array().items(memberSchema)
  });
  
  return schema.validate(data);
}
```

---

## Machine Learning Pipeline

### Model Training Process

**Node.js Implementation:**
```javascript
// Training pipeline
async function trainClassifier(trainingData) {
  const classifier = new natural.LogisticRegressionClassifier(stemmer);
  
  // Add training examples
  for (const corpus of trainingData) {
    for (const item of corpus.data) {
      if (item.intent !== 'None') {
        for (const utterance of item.utterances) {
          const features = extractFeatures(utterance);
          classifier.addDocument(features, item.intent);
        }
      }
    }
  }
  
  // Train and save
  await classifier.train();
  const modelData = JSON.stringify(classifier);
  await fs.writeFile(MODEL_PATH, modelData, 'utf8');
  
  return classifier;
}
```

**Python Implementation:**
```python
def train_classifier(training_files: List[str]) -> Pipeline:
    """Train scikit-learn pipeline with TF-IDF and LogisticRegression."""
    texts = []
    intents = []
    
    # Load training data
    for file_path in training_files:
        corpus = load_json_file(file_path)
        for item in corpus['data']:
            if item['intent'] != 'None':
                for utterance in item['utterances']:
                    texts.append(utterance)
                    intents.append(item['intent'])
    
    # Create and train pipeline
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            tokenizer=tokenize, 
            ngram_range=(1, 3)
        )),
        ('clf', LogisticRegression(
            random_state=42,
            solver='lbfgs'
        ))
    ])
    
    pipeline.fit(texts, intents)
    
    # Save model
    joblib.dump(pipeline, MODEL_FILE)
    
    return pipeline
```

### Model Evaluation

```python
# Model evaluation script
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score

def evaluate_model(classifier, X_test, y_test):
    """Evaluate model performance."""
    predictions = classifier.predict(X_test)
    
    # Classification report
    report = classification_report(y_test, predictions)
    print("Classification Report:")
    print(report)
    
    # Cross-validation
    cv_scores = cross_val_score(classifier, X_test, y_test, cv=5)
    print(f"Cross-validation scores: {cv_scores}")
    print(f"Average CV score: {cv_scores.mean():.3f}")
    
    return {
        'classification_report': report,
        'cv_scores': cv_scores,
        'average_score': cv_scores.mean()
    }
```

---

## Deployment

### Environment Setup

**Production Environment Variables:**
```env
NODE_ENV=production
PORT=3000
LOG_LEVEL=info
```

### Docker Deployment

**Node.js Dockerfile:**
```dockerfile
FROM node:16-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY src/ ./src/
COPY .env ./

EXPOSE 3000

CMD ["npm", "start"]
```

**Python Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 3000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
```

### Health Checks

```javascript
// Health check endpoint
app.get('/health', (req, res) => {
  const health = {
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    chatbot: chatbotProcessor ? 'initialized' : 'not initialized'
  };
  
  res.json(health);
});
```

### Monitoring

```javascript
// Performance monitoring
const responseTime = require('response-time');

app.use(responseTime((req, res, time) => {
  console.log(`${req.method} ${req.url} - ${time}ms`);
  
  // Log slow requests
  if (time > 1000) {
    console.warn(`Slow request: ${req.method} ${req.url} - ${time}ms`);
  }
}));
```

---

## Contributing

### Getting Started

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes**: Follow coding standards and add tests
4. **Run tests**: Ensure all tests pass
5. **Commit changes**: Use conventional commit format
6. **Push to branch**: `git push origin feature/amazing-feature`
7. **Open Pull Request**: Provide clear description

### Pull Request Guidelines

**PR Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Code Review Checklist

**For Reviewers:**
- [ ] Code follows project standards
- [ ] Tests are comprehensive
- [ ] Documentation is updated
- [ ] Performance implications considered
- [ ] Security implications reviewed
- [ ] Breaking changes documented

### Issue Reporting

**Bug Report Template:**
```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Ubuntu 20.04]
- Node.js version: [e.g., 16.14.0]
- Browser: [if applicable]

## Additional Context
Any other relevant information
```

### Development Best Practices

1. **Write tests first** (TDD approach)
2. **Keep functions small** and focused
3. **Use meaningful variable names**
4. **Handle errors gracefully**
5. **Document complex logic**
6. **Optimize for readability**
7. **Follow SOLID principles**
8. **Regular refactoring**

This development guide provides comprehensive information for contributors to effectively work on the RHCP Chatbot project, ensuring code quality, consistency, and maintainability.