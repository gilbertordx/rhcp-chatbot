'use strict';
const fs = require('fs');
const path = require('path');

/**
 * RHCP Corpus Seeder
 * 
 * This seeder loads the RHCP chatbot corpus into the database.
 * It reads the corpus.json file and transforms the intents into
 * knowledge entries that can be used by the chatbot.
 * 
 * The seeder follows the Sequelize migration pattern with:
 * - up(): Loads the corpus data into the database
 * - down(): Removes the corpus data from the database
 */

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    // Read the corpus file from the data directory
    const corpusPath = path.join(__dirname, '../data/rhcp-corpus.json');
    const corpusData = JSON.parse(fs.readFileSync(corpusPath, 'utf8'));

    // Transform each intent in the corpus into a knowledge entry
    const knowledgeEntries = corpusData.data.map(intent => {
      // Create a base entry for the intent with:
      // - type: identifies this as an intent entry
      // - title: the intent name (e.g., "band.members")
      // - content: contains utterances and possible answers
      // - metadata: additional info like locale
      // - tags: derived from the intent name for easier searching
      const baseEntry = {
        type: 'intent',
        title: intent.intent,
        content: {
          utterances: intent.utterances,
          answers: intent.answers
        },
        metadata: {
          locale: corpusData.locale
        },
        tags: intent.intent.split('.'),
        createdAt: new Date(),
        updatedAt: new Date()
      };

      return baseEntry;
    });

    // Insert all knowledge entries into the rhcp_knowledge table
    await queryInterface.bulkInsert('rhcp_knowledge', knowledgeEntries, {});
  },

  async down(queryInterface, Sequelize) {
    // Remove all intent entries from the rhcp_knowledge table
    // This is used when rolling back the seeder
    await queryInterface.bulkDelete('rhcp_knowledge', {
      type: 'intent'
    }, {});
  }
}; 