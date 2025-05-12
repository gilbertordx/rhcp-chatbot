/**
 * Chat Routes
 * 
 * This module defines all chat-related endpoints for the RHCP chatbot.
 * It handles message processing, chat history, and conversation management.
 */

const express = require('express');
const router = express.Router();
const chatController = require('../controllers/chat.controller');

// Send a message to the chatbot
router.post('/', chatController.sendMessage);

// Get chat history for the current user
router.get('/history', chatController.getHistory);

// Clear chat history for the current user
router.delete('/history', chatController.clearHistory);

module.exports = router; 