const express = require('express');
const router = express.Router();
const knowledgeController = require('../controllers/knowledgeController');

// Get all knowledge entries with optional filtering
router.get('/', knowledgeController.getAllKnowledge);

// Get a single knowledge entry by ID
router.get('/:id', knowledgeController.getKnowledgeById);

// Create a new knowledge entry
router.post('/', knowledgeController.createKnowledge);

// Update an existing knowledge entry
router.put('/:id', knowledgeController.updateKnowledge);

// Delete a knowledge entry
router.delete('/:id', knowledgeController.deleteKnowledge);

module.exports = router; 