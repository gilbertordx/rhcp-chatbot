const fs = require('fs').promises;
const path = require('path');
const natural = require('natural');
const ChatbotProcessor = require('./chatbotProcessor');

async function initializeChatbot() {
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

        const trainingData = {
            base: baseCorpus,
            rhcp: rhcpCorpus
        };

        const staticData = {
            bandInfo,
            discography
        };

        // Train the classifier
        console.log('Training NLU classifier...');
        const classifier = new natural.LogisticRegressionClassifier();
        for (const corpus of [baseCorpus, rhcpCorpus]) {
            for (const item of corpus.data) {
                if (item.intent !== 'None') { // Exclude the 'None' intent for training
                    for (const utterance of item.utterances) {
                        classifier.addDocument(utterance, item.intent);
                    }
                }
            }
        }
        await classifier.train();
        console.log('NLU classifier trained.');

        // Initialize ChatbotProcessor after data is loaded and classifier is trained
        const chatbotProcessor = new ChatbotProcessor(classifier, trainingData, staticData);

        console.log('Chatbot initialized successfully');
        return chatbotProcessor;

    } catch (error) {
        console.error('Error initializing chatbot:', error);
        throw error; // Re-throw the error so the caller knows initialization failed
    }
}

module.exports = { initializeChatbot }; 