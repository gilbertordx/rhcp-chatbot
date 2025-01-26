require('dotenv').config();

const sqlConfig = {
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME,
    host: process.env.DB_HOST,
    dialect: process.env.DB_DIALECT || 'postgres',
    port: process.env.DB_PORT,
};

const config = {
    local: sqlConfig, 
};

module.exports = config;