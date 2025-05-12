const { RHCPKnowledge } = require('../database/models');
const { Op } = require('sequelize');

/**
 * Get all knowledge entries with optional filtering
 */
exports.getAllKnowledge = async (req, res) => {
  try {
    const { type, tag, search } = req.query;
    const where = {};

    if (type) {
      where.type = type;
    }

    if (tag) {
      where.tags = {
        [Op.contains]: [tag]
      };
    }

    if (search) {
      where[Op.or] = [
        { title: { [Op.iLike]: `%${search}%` } },
        { content: { [Op.iLike]: `%${search}%` } }
      ];
    }

    const entries = await RHCPKnowledge.findAll({
      where,
      order: [['createdAt', 'DESC']]
    });

    res.json(entries);
  } catch (error) {
    console.error('Error fetching knowledge:', error);
    res.status(500).json({ error: 'Failed to fetch knowledge entries' });
  }
};

/**
 * Get a single knowledge entry by ID
 */
exports.getKnowledgeById = async (req, res) => {
  try {
    const entry = await RHCPKnowledge.findByPk(req.params.id);
    if (!entry) {
      return res.status(404).json({ error: 'Knowledge entry not found' });
    }
    res.json(entry);
  } catch (error) {
    console.error('Error fetching knowledge entry:', error);
    res.status(500).json({ error: 'Failed to fetch knowledge entry' });
  }
};

/**
 * Create a new knowledge entry
 */
exports.createKnowledge = async (req, res) => {
  try {
    const { type, title, content, metadata, tags } = req.body;

    // Validate required fields
    if (!type || !title || !content) {
      return res.status(400).json({ error: 'Type, title, and content are required' });
    }

    const entry = await RHCPKnowledge.create({
      type,
      title,
      content,
      metadata,
      tags
    });

    res.status(201).json(entry);
  } catch (error) {
    console.error('Error creating knowledge entry:', error);
    res.status(500).json({ error: 'Failed to create knowledge entry' });
  }
};

/**
 * Update an existing knowledge entry
 */
exports.updateKnowledge = async (req, res) => {
  try {
    const { id } = req.params;
    const { type, title, content, metadata, tags } = req.body;

    const entry = await RHCPKnowledge.findByPk(id);
    if (!entry) {
      return res.status(404).json({ error: 'Knowledge entry not found' });
    }

    await entry.update({
      type,
      title,
      content,
      metadata,
      tags
    });

    res.json(entry);
  } catch (error) {
    console.error('Error updating knowledge entry:', error);
    res.status(500).json({ error: 'Failed to update knowledge entry' });
  }
};

/**
 * Delete a knowledge entry
 */
exports.deleteKnowledge = async (req, res) => {
  try {
    const { id } = req.params;
    const entry = await RHCPKnowledge.findByPk(id);
    
    if (!entry) {
      return res.status(404).json({ error: 'Knowledge entry not found' });
    }

    await entry.destroy();
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting knowledge entry:', error);
    res.status(500).json({ error: 'Failed to delete knowledge entry' });
  }
}; 