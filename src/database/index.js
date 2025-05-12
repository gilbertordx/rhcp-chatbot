'use strict';

const { Sequelize, DataTypes } = require('sequelize');
const config = require("../../config/db.config.js");
const cls = require('cls-hooked');
const namespace = cls.createNamespace('logbook-db');
const models = require('./models/index');

Sequelize.useCLS(namespace);
const dbConfig = config.development;

const sequelize = new Sequelize(dbConfig.database, dbConfig.username, dbConfig.password, {
  dialect: 'postgres',  
  host: dbConfig.host,
  port: dbConfig.port,
  operatorsAliases: false,
});

const db = {
  sequelize,
  Sequelize,
}

for (const key in models) {
  const model = models[key](sequelize, DataTypes);
  db[model.name] = model;
}

for (const modelName in db) {
  if(db[modelName].associte) {
    db[modelName].associate(db);
  }
}

module.exports = db;