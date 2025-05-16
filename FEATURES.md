# RHCP Chatbot Features

## Natural Language Understanding

The chatbot currently uses a corpus-based approach with a simple classifier (Logistic Regression) to understand user intents and perform basic entity recognition. The system is trained on various RHCP-related topics including:

- Band Information
- Music Catalog
- Interactive Features

**Current Capabilities:**

- Intent classification based on trained utterances.
- Basic entity extraction via dictionary lookup for known members, albums, and songs.
- Simple response generation using corpus answers and basic static data retrieval.
- Confidence thresholding to handle low-confidence classifications.

**Planned Enhancements:**

- Refined entity extraction using more advanced techniques.
- More dynamic and context-aware response generation.
- Potential exploration of different NLU models or libraries for improved accuracy and out-of-scope handling.

### Band Information
- Current band members
- Band history
- Musical style and influences
- Awards and recognition
- Tour information

### Music Catalog
- Album information
- Song details
- Lyrics and meanings
- Release dates
- Production information

### Interactive Features
- Dynamic response selection
- Context-aware conversations
- Entity recognition for songs, albums, and band members
- Multi-turn conversations

## Database Structure

### RHCPKnowledge Model
Stores all the chatbot's knowledge base:
```javascript
{
  type: String,      // Type of knowledge (intent, song, album, etc.)
  title: String,     // Title or name of the entry
  content: JSONB,    // Detailed information
  metadata: JSONB,   // Additional metadata
  tags: String[]     // Searchable tags
}
```

### ChatMessage Model
Tracks all conversations:
```javascript
{
  userId: UUID,      // Reference to the user
  message: Text,     // The actual message
  isBot: Boolean,    // Whether from bot or user
  intent: String,    // Detected intent
  entities: JSONB,   // Extracted entities
  context: JSONB     // Conversation context
}
```

## API Endpoints

### Chat Endpoints
- `POST /api/chat` - Send a message to the chatbot
- `GET /api/chat/history` - Get chat history
- `DELETE /api/chat/history` - Clear chat history

### Knowledge Base Endpoints
- `GET /api/knowledge` - Search knowledge base
- `GET /api/knowledge/:id` - Get specific knowledge entry
- `POST /api/knowledge` - Add new knowledge (admin only)
- `PUT /api/knowledge/:id` - Update knowledge (admin only)
- `DELETE /api/knowledge/:id` - Delete knowledge (admin only)

## Conversation Flow

1. **User Input**
   - User sends a message
   - System preprocesses the text
   - Entity recognition is performed

2. **Intent Matching**
   - System matches against known intents using a classifier.
   - Confidence score is calculated and checked against a threshold.
   - Context is considered (Planned for future phases).

3. **Response Generation**
   - Appropriate response is selected based on confident intent and extracted entities.
   - Dynamic content is inserted from static data or corpus answers.
   - Response is formatted.

4. **Context Management**
   - Conversation state is updated
   - Relevant entities are stored
   - Context is maintained for follow-up questions

## Error Handling

The system includes comprehensive error handling for:
- Invalid user input
- Database connection issues
- Intent matching failures
- API rate limiting
- Authentication errors

## Security Features

- Input sanitization
- Rate limiting
- Authentication for admin endpoints
- Secure database connections
- Environment variable protection 