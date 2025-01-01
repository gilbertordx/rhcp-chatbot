const express = require('express')
const app = express()
const port = 3000

app.get('/', (req, res) =>  {
    res.send('Health!')
})

app.listen(port, () => {
    console.log(`Running app on ${port}`)
})