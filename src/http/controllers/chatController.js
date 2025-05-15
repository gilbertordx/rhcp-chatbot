/**
 * Controller for handling chat message processing.
 */

/**
 * Processes a user chat message using the provided ChatbotProcessor.
 * @param {object} chatbotProcessor - The initialized ChatbotProcessor instance.
 * @param {string} userMessage - The message from the user.
 * @returns {Promise<object>} - The chatbot's response.
 */
async function processChatMessage(chatbotProcessor, userMessage) {
    if (!chatbotProcessor) {
        throw new Error('Chatbot processor is not initialized.');
    }
    if (!userMessage) {
        throw new Error('User message is required.');
    }
    
    return await chatbotProcessor.processMessage(userMessage);
}

module.exports = { processChatMessage }; 