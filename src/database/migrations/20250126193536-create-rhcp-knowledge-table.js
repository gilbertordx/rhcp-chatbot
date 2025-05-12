'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.sequelize.query('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";');
    await queryInterface.createTable('rhcp_knowledge', {
      id: {
        type: Sequelize.UUID,
        defaultValue: Sequelize.literal('uuid_generate_v4()'),
        primaryKey: true,
        allowNull: false,
      },
      type: {
        type: Sequelize.STRING,
        allowNull: false,
        comment: 'Type of knowledge (e.g., "song", "album", "band_member", "intent")'
      },
      title: {
        type: Sequelize.STRING,
        allowNull: false,
        comment: 'Title or name of the entry'
      },
      content: {
        type: Sequelize.JSONB,
        allowNull: false,
        comment: 'The main content or answer'
      },
      category: {
        type: Sequelize.STRING,
        allowNull: false,
        comment: 'Category of the knowledge (e.g., "music", "history", "members")'
      },
      source: {
        type: Sequelize.STRING,
        allowNull: false,
        defaultValue: 'corpus',
        comment: 'Source of the knowledge (e.g., "corpus", "manual", "api")'
      },
      metadata: {
        type: Sequelize.JSONB,
        allowNull: true,
        comment: 'Additional metadata (e.g., utterances, answers, related entries)'
      },
      tags: {
        type: Sequelize.ARRAY(Sequelize.STRING),
        allowNull: true,
        comment: 'Searchable tags for the entry'
      },
      createdAt: {
        type: Sequelize.DATE,
        allowNull: false,
        defaultValue: Sequelize.NOW
      },
      updatedAt: {
        type: Sequelize.DATE,
        allowNull: false,
        defaultValue: Sequelize.NOW
      },
      deletedAt: {
        type: Sequelize.DATE,
        allowNull: true
      }
    });

    // Add indexes
    await queryInterface.addIndex('rhcp_knowledge', ['type']);
    await queryInterface.addIndex('rhcp_knowledge', ['category']);
    await queryInterface.addIndex('rhcp_knowledge', ['title']);
    await queryInterface.addIndex('rhcp_knowledge', ['tags'], { using: 'GIN' });
  },

  async down(queryInterface, Sequelize) {
    await queryInterface.dropTable('rhcp_knowledge');
  }
}; 