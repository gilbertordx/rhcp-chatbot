const fs = require('fs').promises;
const path = require('path');
const natural = require('natural');
const express = require('express');
const bodyParser = require('body-parser');
const ChatbotProcessor = require('./chatbotProcessor');
const { initializeChatbot } = require('./initializer');
const createChatRouter = require('./http/routes/chatRoutes');
const { processChatMessage } = require('./http/controllers/chatController');

class RHCPChatbot {
    constructor() {
        this.trainingData = null;
        this.staticData = null;
        this.classifier = new natural.BayesClassifier();
        this.chatbotProcessor = null;
    }

    async initialize() {
        try {
            const baseCorpus = JSON.parse(
                await fs.readFile(path.join(__dirname, 'data/training/base-corpus.json'), 'utf8')
            );
            const rhcpCorpus = JSON.parse(
                await fs.readFile(path.join(__dirname, 'data/training/rhcp-corpus.json'), 'utf8')
            );

            const bandInfo = JSON.parse(
                await fs.readFile(path.join(__dirname, 'data/static/band-info.json'), 'utf8')
            );
            const discography = JSON.parse(
                await fs.readFile(path.join(__dirname, 'data/static/discography.json'), 'utf8')
            );

            this.trainingData = {
                base: baseCorpus,
                rhcp: rhcpCorpus
            };

            this.staticData = {
                bandInfo,
                discography
            };

            console.log('Training NLU classifier...');
            for (const corpus of [baseCorpus, rhcpCorpus]) {
                for (const item of corpus.data) {
                    if (item.intent !== 'None') {
                        for (const utterance of item.utterances) {
                            this.classifier.addDocument(utterance, item.intent);
                        }
                    }
                }
            }
            await this.classifier.train();
            console.log('NLU classifier trained.');

            this.chatbotProcessor = new ChatbotProcessor(this.classifier, this.trainingData, this.staticData);

            console.log('Chatbot initialized successfully');
        } catch (error) {
            console.error('Error initializing chatbot:', error);
            throw error;
        }
    }
}

const app = express();

app.use(bodyParser.json());


const PORT = process.env.PORT || 3000;

async function startServer() {
    try {
        const chatbotProcessor = await initializeChatbot();
        
        app.use('/api/chat', createChatRouter(chatbotProcessor, processChatMessage));

        app.listen(PORT, () => {
            console.log(`Server is running on port ${PORT}`);
            console.log('RHCP Chatbot is ready to chat!');
        });
    } catch (error) {
        console.error('Failed to start server or initialize chatbot:', error);
        process.exit(1);
    }
}

startServer();

module.exports = app;