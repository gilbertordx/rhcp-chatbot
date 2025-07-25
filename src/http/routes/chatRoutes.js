const express = require('express');

/**
 * Sets up chat-related routes.
 * @param {object} chatbotProcessor - The initialized ChatbotProcessor instance.
 * @param {function} chatController - The controller function for processing chat messages.
 * @returns {object} - The Express router with chat routes.
 */
module.exports = (chatbotProcessor, chatController) => {
    const router = express.Router();

    router.post('/', async (req, res) => {
        const userMessage = req.body.message;

        try {
            const chatbotResponse = await chatController(chatbotProcessor, userMessage);
            
            if (chatbotProcessor && chatbotProcessor.classifier) {
                 const classifications = chatbotProcessor.classifier.getClassifications(userMessage.toLowerCase());
                 return res.json({...chatbotResponse, classifications: classifications});
            }
            return res.json(chatbotResponse);
            
        } catch (error) {
            console.error('Error processing message in chat route:', error);
            if (error.message === 'User message is required.') {
                 return res.status(400).json({ error: error.message });
            }
            if (error.message === 'Chatbot processor is not initialized.') {
                 return res.status(503).json({ error: error.message });
            }
            res.status(500).json({ error: 'An error occurred while processing your message.' });
        }
    });

    return router;
}; 