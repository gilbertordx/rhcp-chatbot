const { initializeChatbot } = require('../src/initializer');
const { processChatMessage } = require('../src/http/controllers/chatController');

describe('Chatbot Processor', () => {
    let chatbotProcessor;

    // Initialize the chatbot before running tests
    beforeAll(async () => {
        chatbotProcessor = await initializeChatbot();
    }, 30000); // Increase timeout for initialization

    // Test case for a simple greeting
    test('should handle a simple greeting', async () => {
        const response = await processChatMessage(chatbotProcessor, 'Hello');
        expect(response.intent).toBe('greetings.hello');
        expect(response.message).toBeDefined(); // Expect a message to be returned
        expect(response.message.length).toBeGreaterThan(0); // Expect the message not to be empty
    });

    // Test case for the problematic band members query
    test('should correctly classify and respond to band members query', async () => {
        const response = await processChatMessage(chatbotProcessor, 'Who are the members of the band?');
        expect(response.intent).toBe('band.members'); // Expecting the correct intent
        expect(response.message).toContain('Current members:'); // Expect the specific response using static data
    });

     // Test case for an out-of-scope query
    test('should return a fallback for out-of-scope queries', async () => {
        const response = await processChatMessage(chatbotProcessor, 'Tell me about quantum physics');
        expect(response.intent).toBe('unrecognized'); // Expecting the unrecognized intent due to low confidence
        expect(response.message).toBe('Sorry, I didn\'t understand that.'); // Expect the default fallback message
    });

    // Add more test cases for other intents as needed

    // Test case for agent.chatbot
    test('should handle agent.chatbot intent', async () => {
        const response = await processChatMessage(chatbotProcessor, 'are you a bot');
        expect(response.intent).toBe('agent.chatbot');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

    // Test case for greetings.bye
    test('should handle greetings.bye intent', async () => {
        const response = await processChatMessage(chatbotProcessor, 'bye for now');
        expect(response.intent).toBe('greetings.bye');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

    // Test case for band.history
    test('should handle band.history intent', async () => {
        const response = await processChatMessage(chatbotProcessor, 'when was RHCP formed');
        expect(response.intent).toBe('band.history');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

    // Test case for album.info
    test('should handle album.info intent', async () => {
        const response = await processChatMessage(chatbotProcessor, 'list their albums');
        expect(response.intent).toBe('album.info');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

    // Test case for song.info
    test('should handle song.info intent', async () => {
        const response = await processChatMessage(chatbotProcessor, 'name some of their songs');
        expect(response.intent).toBe('song.info');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

}); 