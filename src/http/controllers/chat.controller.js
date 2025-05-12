/**
 * Chat Controller
 * 
 * This module handles all chat-related operations.
 * It provides methods for processing messages, managing chat history,
 * and handling conversation context.
 */

const { ChatMessage, RHCPKnowledge } = require('../../models');
const { Op } = require('sequelize');
const natural = require('natural');
const tokenizer = new natural.WordTokenizer();

/**
 * Process a message and generate a response
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 */
exports.sendMessage = async (req, res) => {
    try {
        const { message } = req.body;
        const userId = req.user.id;

        if (!message || message.trim() === '') {
            return res.status(400).json({ error: 'Message cannot be empty' });
        }

        // Save user message
        const userMessage = await ChatMessage.create({
            userId,
            message,
            isBot: false
        });

        // Process message and generate response
        const response = await processMessage(message);

        // Save bot response
        const botMessage = await ChatMessage.create({
            userId,
            message: response.message,
            isBot: true,
            intent: response.intent,
            entities: response.entities,
            context: response.context
        });

        res.json({
            message: response.message,
            intent: response.intent,
            entities: response.entities
        });
    } catch (error) {
        console.error('Error processing message:', error);
        res.status(500).json({ error: 'Failed to process message' });
    }
};

/**
 * Get chat history for the current user
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 */
exports.getHistory = async (req, res) => {
    try {
        const userId = req.user.id;
        const { limit = 50, offset = 0 } = req.query;

        const messages = await ChatMessage.findAll({
            where: { userId },
            order: [['createdAt', 'DESC']],
            limit: parseInt(limit),
            offset: parseInt(offset)
        });

        res.json(messages);
    } catch (error) {
        console.error('Error getting chat history:', error);
        res.status(500).json({ error: 'Failed to get chat history' });
    }
};

/**
 * Clear chat history for the current user
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 */
exports.clearHistory = async (req, res) => {
    try {
        const userId = req.user.id;

        await ChatMessage.destroy({
            where: { userId }
        });

        res.status(204).send();
    } catch (error) {
        console.error('Error clearing chat history:', error);
        res.status(500).json({ error: 'Failed to clear chat history' });
    }
};

/**
 * Process a message and generate a response
 * @param {string} message - The user's message
 * @returns {Object} The response object
 */
async function processMessage(message) {
    // Tokenize the message
    const tokens = tokenizer.tokenize(message.toLowerCase());

    // Search for relevant knowledge
    const knowledge = await RHCPKnowledge.findAll({
        where: {
            [Op.or]: [
                { title: { [Op.iLike]: `%${message}%` } },
                { content: { [Op.iLike]: `%${message}%` } }
            ]
        },
        limit: 5
    });

    // If we found relevant knowledge, use it
    if (knowledge.length > 0) {
        const bestMatch = knowledge[0];
        return {
            message: bestMatch.content,
            intent: 'knowledge',
            entities: {
                type: bestMatch.type,
                title: bestMatch.title
            },
            context: {
                source: bestMatch.source,
                metadata: bestMatch.metadata
            }
        };
    }

    // If no specific knowledge found, use a default response
    return {
        message: "I'm sorry, I don't have specific information about that. Could you try asking something else about RHCP?",
        intent: 'unknown',
        entities: {},
        context: {}
    };
} 