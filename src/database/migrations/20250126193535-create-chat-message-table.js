'use strict';

/** @type {import('sequelize-cli').Migration} */
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable('chat_messages', {
      id: {
        type: Sequelize.UUID,
        defaultValue: Sequelize.UUIDV4,
        primaryKey: true,
        allowNull: false,
      },
      user_id: {
        type: Sequelize.INTEGER,
        allowNull: false,
        references: {
          model: 'users',
          key: 'id'
        },
        onUpdate: 'CASCADE',
        onDelete: 'CASCADE'
      },
      message: {
        type: Sequelize.JSONB,
        allowNull: false
      },
      is_bot: {
        type: Sequelize.BOOLEAN,
        allowNull: false,
        defaultValue: false
      },
      intent: {
        type: Sequelize.STRING,
        allowNull: true,
        comment: 'The detected intent of the message (e.g., "song_info", "band_history", "album_info")'
      },
      entities: {
        type: Sequelize.JSONB,
        allowNull: true,
        comment: 'Extracted entities from the message (e.g., song names, album names, band members)'
      },
      context: {
        type: Sequelize.JSONB,
        allowNull: true,
        comment: 'Additional context for the conversation'
      },
      created_at: {
        type: Sequelize.DATE,
        allowNull: false,
        defaultValue: Sequelize.NOW
      },
      updated_at: {
        type: Sequelize.DATE,
        allowNull: false,
        defaultValue: Sequelize.NOW
      },
      deleted_at: {
        type: Sequelize.DATE,
        allowNull: true
      }
    });

    // Add indexes
    await queryInterface.addIndex('chat_messages', ['user_id']);
    await queryInterface.addIndex('chat_messages', ['created_at']);
    await queryInterface.addIndex('chat_messages', ['intent']);
  },

  async down(queryInterface, Sequelize) {
    await queryInterface.dropTable('chat_messages');
  }
}; 