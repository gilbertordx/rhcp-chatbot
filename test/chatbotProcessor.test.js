const { initializeChatbot } = require('../src/initializer');
const { processChatMessage } = require('../src/http/controllers/chatController');

describe('Chatbot Processor', () => {
    let chatbotProcessor;
    let chatbotProcessorInstance;

    beforeAll(async () => {
        if (!chatbotProcessorInstance) {
            chatbotProcessorInstance = await initializeChatbot();
        }
        chatbotProcessor = chatbotProcessorInstance;
    }, 300000);

    test('should handle a simple greeting', async () => {
        const response = await processChatMessage(chatbotProcessor, 'Hello');
        expect(response.intent).toBe('greetings.hello');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

    test('should correctly classify and respond to band members query', async () => {
        const response = await processChatMessage(chatbotProcessor, 'Who are the members of the band?');
        expect(response.intent).toBe('band.members');
        expect(response.message).toMatch(/Anthony Kiedis.*Flea.*John Frusciante.*Chad Smith/i);
    });

    test('should correctly classify out-of-scope queries and provide an appropriate response', async () => {
        const response = await processChatMessage(chatbotProcessor, 'Tell me about quantum physics');
        expect(response.intent).toBe('intent.outofscope');
        const oosAnswers = [
            "Sorry, I can only help with questions about the Red Hot Chili Peppers.",
            "That's a bit outside of what I know. I'm focused on the Red Hot Chili Peppers.",
            "I'm not equipped to answer that. My expertise is the Red Hot Chili Peppers.",
            "My knowledge is limited to the Red Hot Chili Peppers. Is there anything about them I can help with?"
        ];
        expect(oosAnswers).toContain(response.message);
    });

    test('should handle agent.chatbot intent', async () => {
        const response = await processChatMessage(chatbotProcessor, 'are you a bot');
        expect(response.intent).toBe('agent.chatbot');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

    test('should handle greetings.bye intent', async () => {
        const response = await processChatMessage(chatbotProcessor, 'bye for now');
        expect(response.intent).toBe('greetings.bye');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

    test('should handle band.history intent', async () => {
        const response = await processChatMessage(chatbotProcessor, 'when was RHCP formed');
        expect(response.intent).toBe('band.history');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

    test('should handle album.info intent', async () => {
        const response = await processChatMessage(chatbotProcessor, 'list their albums');
        expect(response.intent).toBe('album.info');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

    test('should handle song.info intent', async () => {
        const response = await processChatMessage(chatbotProcessor, 'name some of their songs');
        expect(response.intent).toBe('song.info');
        expect(response.message).toBeDefined();
        expect(response.message.length).toBeGreaterThan(0);
    });

}); 