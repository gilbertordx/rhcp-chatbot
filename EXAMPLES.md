# RHCP Chatbot Examples

## Basic Usage

### Starting a Conversation
```bash
# Using curl
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, tell me about RHCP"}'

# Expected Response
{
  "response": "Hello! I'm your RHCP expert. I can tell you about the band members, their music, albums, and more. What would you like to know?",
  "intent": "greeting"
}
```

### Asking About Band Members
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Who are the current members of RHCP?"}'

# Expected Response
{
  "response": "The current members of Red Hot Chili Peppers are Anthony Kiedis (vocals), Flea (bass), John Frusciante (guitar), and Chad Smith (drums).",
  "intent": "band.members"
}
```

### Asking About Albums
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What albums do they have?"}'

# Expected Response
{
  "response": "Some of their most famous albums include 'Blood Sugar Sex Magik' (1991), 'Californication' (1999), 'By the Way' (2002), 'Stadium Arcadium' (2006), and 'Unlimited Love' (2022).",
  "intent": "album.info"
}
```

## Multi-turn Conversations

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

## Using the API

### Getting Chat History
```bash
curl -X GET http://localhost:8080/api/chat/history \
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
curl -X GET "http://localhost:8080/api/knowledge?query=californication" \
  -H "Content-Type: application/json"

# Expected Response
{
  "results": [
    {
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

## Error Handling Examples

### Invalid Input
```bash
curl -X POST http://localhost:8080/api/chat \
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