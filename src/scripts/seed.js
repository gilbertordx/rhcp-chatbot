/**
 * Database Seeding Script
 * 
 * This script populates the database with initial RHCP knowledge
 * from the corpus.json file.
 */

require('dotenv').config();
const fs = require('fs').promises;
const path = require('path');
const { sequelize } = require('../models');
const { RHCPKnowledge } = require('../models');

async function seed() {
    try {
        // Read corpus file
        const corpusPath = path.join(__dirname, '../../corpus.json');
        const corpusData = await fs.readFile(corpusPath, 'utf8');
        const corpus = JSON.parse(corpusData);

        // Connect to database
        await sequelize.authenticate();
        console.log('Connected to database');

        // Clear existing knowledge
        await RHCPKnowledge.destroy({ where: {} });
        console.log('Cleared existing knowledge');

        // Process and insert knowledge
        const knowledgeEntries = corpus.map(entry => ({
            type: entry.intent,
            title: entry.intent,
            content: entry.answers[0], // Use first answer as content
            metadata: {
                utterances: entry.utterances,
                answers: entry.answers
            },
            source: 'corpus',
            category: entry.intent.split('.')[0] // Use first part of intent as category
        }));

        await RHCPKnowledge.bulkCreate(knowledgeEntries);
        console.log(`Inserted ${knowledgeEntries.length} knowledge entries`);

        console.log('Seeding completed successfully');
        process.exit(0);
    } catch (error) {
        console.error('Error seeding database:', error);
        process.exit(1);
    }
}

seed(); 