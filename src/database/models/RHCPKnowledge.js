'use strict';
const { Model } = require('sequelize');

module.exports = (sequelize, DataTypes) => {
  class RHCPKnowledge extends Model {
    static associate(models) {
      // Define associations here if needed
    }
  }

  RHCPKnowledge.init({
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true
    },
    type: {
      type: DataTypes.STRING,
      allowNull: false,
      comment: 'Type of knowledge (song, album, band_member, event, etc.)'
    },
    title: {
      type: DataTypes.STRING,
      allowNull: false,
      comment: 'Title of the song, album, or name of the band member'
    },
    content: {
      type: DataTypes.JSONB,
      allowNull: false,
      comment: 'Detailed information about the entry'
    },
    metadata: {
      type: DataTypes.JSONB,
      allowNull: true,
      comment: 'Additional metadata like release dates, durations, etc.'
    },
    tags: {
      type: DataTypes.ARRAY(DataTypes.STRING),
      allowNull: true,
      comment: 'Tags for easier searching and categorization'
    }
  }, {
    sequelize,
    modelName: 'RHCPKnowledge',
    tableName: 'rhcp_knowledge',
    timestamps: true
  });

  return RHCPKnowledge;
}; 