/**
 * Main Application File
 * 
 * This is the entry point of the RHCP Chatbot application.
 * It initializes the chatbot with training data and provides
 * the core message handling functionality.
 */

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
            // Load training data
            const baseCorpus = JSON.parse(
                await fs.readFile(path.join(__dirname, 'data/training/base-corpus.json'), 'utf8')
            );
            const rhcpCorpus = JSON.parse(
                await fs.readFile(path.join(__dirname, 'data/training/rhcp-corpus.json'), 'utf8')
            );

            // Load static data
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

            // Train the classifier
            console.log('Training NLU classifier...');
            for (const corpus of [baseCorpus, rhcpCorpus]) {
                for (const item of corpus.data) {
                    if (item.intent !== 'None') { // Exclude the 'None' intent for training
                        for (const utterance of item.utterances) {
                            this.classifier.addDocument(utterance, item.intent);
                        }
                    }
                }
            }
            await this.classifier.train();
            console.log('NLU classifier trained.');

            // Initialize ChatbotProcessor after data is loaded and classifier is trained
            this.chatbotProcessor = new ChatbotProcessor(this.classifier, this.trainingData, this.staticData);

            console.log('Chatbot initialized successfully');
        } catch (error) {
            console.error('Error initializing chatbot:', error);
            throw error;
        }
    }
}

// Create and initialize chatbot (Initialization moved to startServer)
// const chatbot = new RHCPChatbot(); // Removed

// Initialize Express app
const app = express();

// Middleware
app.use(bodyParser.json());
// Add other middleware like CORS, Helmet, Morgan later if needed as per README

// Mount chat routes
// const chatbotProcessor = await initializeChatbot(); // Initialize in startServer
// app.post('/api/chat', async (req, res) => { ... }); // Removed

// Start the server and initialize the chatbot
const PORT = process.env.PORT || 3000;

async function startServer() {
    try {
        // Initialize the chatbot components
        const chatbotProcessor = await initializeChatbot();
        
        // Mount the chat router, passing the initialized processor and controller
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

// Export the app for testing purposes (optional)
module.exports = app;