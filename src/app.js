const express = require('express')
require("dotenv").config();

const app = express()
const port = process.env.NODE_DOCKER_PORT || 8080;

app.use(express.json());

app.get('/', (req, res) => {
    res.send('Health!')
})

app.listen(port, () => {
    console.log(`Running app on ${port}`)
})