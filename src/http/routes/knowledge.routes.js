/**
 * Knowledge Base Routes
 * 
 * This module defines all knowledge base-related endpoints.
 * It handles searching, retrieving, and managing the RHCP knowledge database.
 */

const express = require('express');
const router = express.Router();
const knowledgeController = require('../../controllers/knowledgeController');
const authMiddleware = require('../middleware/auth.middleware');

// Public routes
router.get('/', knowledgeController.getAllKnowledge);
router.get('/:id', knowledgeController.getKnowledgeById);

// Protected routes (admin only)
router.post('/', authMiddleware.isAdmin, knowledgeController.createKnowledge);
router.put('/:id', authMiddleware.isAdmin, knowledgeController.updateKnowledge);
router.delete('/:id', authMiddleware.isAdmin, knowledgeController.deleteKnowledge);

module.exports = router; 