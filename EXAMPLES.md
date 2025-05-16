# RHCP Chatbot Examples

This document provides examples of how to interact with the RHCP Chatbot.

## Basic Usage

### Starting a Conversation
```bash
# Using curl (assuming the server is running on port 3000)
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, tell me about RHCP"}'

# Expected Response (structure may vary slightly based on implementation details)
{
  "message": "Hey there!",
  "intent": "greetings.hello",
  "entities": [],
  "confidence": 0.9 // Example confidence score
}
```

### Asking About Band Members
```bash
# Using curl (assuming the server is running on port 3000)
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Who are the current members of RHCP?"}'

# Expected Response (based on current implementation using static data for this intent)
{
  "message": "Current members: Anthony Kiedis, Flea, John Frusciante, and Chad Smith. Former notable members: Hillel Slovak, Jack Irons, Dave Navarro, Josh Klinghoffer.",
  "intent": "band.members",
  "entities": [],
  "confidence": 0.75 // Example confidence score
}
```

### Asking About Albums
```bash
# Using curl (assuming the server is running on port 3000)
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What albums do they have?"}'

# Expected Response (based on current implementation using corpus data)
{
  "message": "Some of their most famous albums include 'Blood Sugar Sex Magik' (1991), 'Californication' (1999), 'By the Way' (2002), 'Stadium Arcadium' (2006), and 'Unlimited Love' (2022).",
  "intent": "album.info",
  "entities": [],
  "confidence": 0.85 // Example confidence score
}
```

## Multi-turn Conversations (Planned for future phases)

These examples illustrate the desired flow for multi-turn interactions, which will be implemented in later development phases.

### Example 1: Album Details
```
User: Tell me about Californication
Bot: 'Californication' is RHCP's seventh studio album, released in 1999. It features hits like 'Scar Tissue', 'Otherside', and the title track 'Californication'. The album marked John Frusciante's return to the band.

User: What songs are on it?
Bot: The album includes 15 tracks, with some of the most popular being:
- Scar Tissue
- Around the World
- Otherside
- Californication
- Road Trippin'
Would you like to know more about any specific song?

User: Tell me about Scar Tissue
Bot: 'Scar Tissue' is one of RHCP's most successful songs. It won a Grammy for Best Rock Song in 2000. The song's lyrics deal with addiction and recovery, themes that are personal to Anthony Kiedis.
```

### Example 2: Band History
```
User: When was RHCP formed?
Bot: Red Hot Chili Peppers was formed in 1983 in Los Angeles, California. The original members were Anthony Kiedis, Flea, Hillel Slovak, and Jack Irons.

User: Who was their first guitarist?
Bot: Hillel Slovak was the band's first guitarist. He was a founding member and played on their first two albums before his tragic death in 1988.

User: What happened after that?
Bot: After Hillel's death, the band went through a difficult period. They initially disbanded but later reformed with John Frusciante as their new guitarist. This led to their breakthrough album 'Blood Sugar Sex Magik' in 1991.
```

## Using the API (Planned for future phases beyond basic chat)

These endpoints are planned for implementation in later development phases to support features like chat history and knowledge base management.

### Getting Chat History
```bash
curl -X GET http://localhost:3000/api/chat/history \
  -H "Content-Type: application/json"

# Expected Response
{
  "history": [
    {
      "message": "Who are the current members of RHCP?",
      "response": "The current members...",
      "timestamp": "2024-03-10T12:00:00Z"
    },
    // ... more messages
  ]
}
```

### Searching Knowledge Base
```bash
curl -X GET "http://localhost:3000/api/knowledge?query=californication" \
  -H "Content-Type: application/json"

# Expected Response
{
  "results": [
    { Hartley:
      "type": "album",
      "title": "Californication",
      "content": {
        "releaseDate": "1999",
        "tracks": [...],
        "producer": "Rick Rubin"
      }
    }
  ]
}
```

## Error Handling Examples (Planned for future phases)

These examples illustrate planned error handling responses.

### Invalid Input
```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": ""}'

# Expected Response
{
  "error": "Message cannot be empty",
  "status": 400
}
```

### Rate Limiting
```bash
# After too many requests
{
  "error": "Too many requests. Please try again later.",
  "status": 429
}
```

## Best Practices

1. **Be Specific**: Ask specific questions for better responses
   - Good: "What's the story behind Under the Bridge?"
   - Less Good: "Tell me about their songs"

2. **Follow-up Questions**: Use context from previous responses
   - Good: "What album is that from?"
   - Less Good: "What albums do they have?"

3. **Use Natural Language**: The bot understands conversational language
   - Good: "Who plays bass in the band?"
   - Also Good: "Who's the bassist?"

4. **Be Patient**: Some responses might take a moment to generate
   - The bot processes natural language and searches its knowledge base
   - Complex questions might take longer to answer 