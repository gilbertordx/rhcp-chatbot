'use strict';
const { Model } = require('sequelize');

module.exports = (sequelize, DataTypes) => {
  class ChatMessage extends Model {
    static associate(models) {
      // Define associations here
      ChatMessage.belongsTo(models.User, {
        foreignKey: 'userId',
        as: 'user'
      });
    }
  }

  ChatMessage.init({
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true
    },
    userId: {
      type: DataTypes.UUID,
      allowNull: false,
      references: {
        model: 'Users',
        key: 'id'
      }
    },
    message: {
      type: DataTypes.TEXT,
      allowNull: false
    },
    isBot: {
      type: DataTypes.BOOLEAN,
      allowNull: false,
      defaultValue: false
    },
    intent: {
      type: DataTypes.STRING,
      allowNull: true,
      comment: 'The detected intent of the message (e.g., "song_info", "band_history", "album_info")'
    },
    entities: {
      type: DataTypes.JSONB,
      allowNull: true,
      comment: 'Extracted entities from the message (e.g., song names, album names, band members)'
    },
    context: {
      type: DataTypes.JSONB,
      allowNull: true,
      comment: 'Additional context for the conversation'
    }
  }, {
    sequelize,
    modelName: 'ChatMessage',
    tableName: 'chat_messages',
    timestamps: true
  });

  return ChatMessage;
}; 