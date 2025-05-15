const express = require('express');

/**
 * Sets up chat-related routes.
 * @param {object} chatbotProcessor - The initialized ChatbotProcessor instance.
 * @param {function} chatController - The controller function for processing chat messages.
 * @returns {object} - The Express router with chat routes.
 */
module.exports = (chatbotProcessor, chatController) => {
    const router = express.Router();

    // Chatbot API Endpoint
    router.post('/', async (req, res) => {
        const userMessage = req.body.message;

        try {
            // Use the controller to process the message
            const chatbotResponse = await chatController(chatbotProcessor, userMessage);
            
            // Temporarily add classifications for debugging
            if (chatbotProcessor && chatbotProcessor.classifier) {
                 const classifications = chatbotProcessor.classifier.getClassifications(userMessage.toLowerCase());
                 res.json({...chatbotResponse, classifications: classifications});
            } else {
                res.json(chatbotResponse);
            }
            
        } catch (error) {
            console.error('Error processing message in chat route:', error);
            // More specific error handling can be added here based on error types
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