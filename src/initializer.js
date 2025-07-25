const fs = require('fs').promises;
const path = require('path');
const natural = require('natural');
const ChatbotProcessor = require('./chatbotProcessor');

const stemmer = natural.PorterStemmer;
const tokenizer = new natural.WordTokenizer(); // For tokenizing before NGrams
// const stopwords = natural.stopwords; // Reverted

const MODEL_FILE = path.join(__dirname, 'models', 'logistic_regression_classifier.json');

let chatbotProcessorInstance = null; // Cache for the chatbot processor

async function initializeChatbot() {
    if (chatbotProcessorInstance) {
        console.log('Returning cached NLU classifier and chatbot processor.');
        return chatbotProcessorInstance;
    }

    let classifier;

    try {
        // Always try to load LogisticRegressionClassifier from file first
        try {
            await fs.access(MODEL_FILE);
            console.log('Loading NLU classifier (LogisticRegression) from file...');
            const data = await fs.readFile(MODEL_FILE, 'utf8');
            const modelData = JSON.parse(data);
            classifier = await new Promise((resolve, reject) => {
                natural.LogisticRegressionClassifier.restore(modelData, tokenizer.tokenize, stemmer.stem, (err, restoredClassifier) => {
                    if (err) reject(err); else resolve(restoredClassifier);
                });
            });
            console.log('NLU classifier (LogisticRegression) loaded.');
        } catch (err) {
            if (err.code !== 'ENOENT') throw err; // Re-throw if it's not a "file not found" error
            console.log('LogisticRegression model file not found or error during load, proceeding to train.');
        }

        if (!classifier) { // This block is entered if classifier was not loaded from file
            console.log('Training new NLU classifier (LogisticRegression with unigrams & bigrams & trigrams)...');
            const baseCorpus = JSON.parse(await fs.readFile(path.join(__dirname, 'data/training/base-corpus.json'), 'utf8'));
            const rhcpCorpus = JSON.parse(await fs.readFile(path.join(__dirname, 'data/training/rhcp-corpus.json'), 'utf8'));

            classifier = new natural.LogisticRegressionClassifier(stemmer);

            for (const corpus of [baseCorpus, rhcpCorpus]) {
                for (const item of corpus.data) {
                    if (item.intent !== 'None') {
                        for (const utterance of item.utterances) {
                            const tokens = tokenizer.tokenize(utterance.toLowerCase());
                            if (tokens && tokens.length > 0) {
                                let features = [];
                                features = features.concat(tokens); // Unigrams
                                if (tokens.length >= 2) { // Bigrams
                                    features = features.concat(natural.NGrams.bigrams(tokens).map(bi => bi.join('_')));
                                }
                                if (tokens.length >= 3) {
                                    features = features.concat(natural.NGrams.trigrams(tokens).map(tri => tri.join('_')));
                                }
                                if (features.length > 0) {
                                    classifier.addDocument(features, item.intent);
                                }
                            }
                        }
                    }
                }
            }
            console.time('classifier.train (LogisticRegression)');
            await classifier.train();
            console.timeEnd('classifier.train (LogisticRegression)');
            console.log('NLU classifier (LogisticRegression) trained.');

            // Always save the model if it was just trained (no longer conditional on NODE_ENV)
            const modelDataToSave = JSON.stringify(classifier);
            await fs.writeFile(MODEL_FILE, modelDataToSave, 'utf8');
            console.log('NLU classifier (LogisticRegression) saved to file.');
        }

        // Load static data regardless of training or loading model
        const bandInfo = JSON.parse(
            await fs.readFile(path.join(__dirname, 'data/static/band-info.json'), 'utf8')
        );
        const discography = JSON.parse(
            await fs.readFile(path.join(__dirname, 'data/static/discography.json'), 'utf8')
        );

        const trainingData = { // We still need training data for other parts of ChatbotProcessor
            base: JSON.parse(await fs.readFile(path.join(__dirname, 'data/training/base-corpus.json'), 'utf8')),
            rhcp: JSON.parse(await fs.readFile(path.join(__dirname, 'data/training/rhcp-corpus.json'), 'utf8'))
        };

        const staticData = {
            bandInfo,
            discography
        };

        const chatbotProcessor = new ChatbotProcessor(classifier, trainingData, staticData);
        chatbotProcessorInstance = chatbotProcessor; // Cache the instance

        console.log('Chatbot initialized successfully');
        return chatbotProcessorInstance;

    } catch (error) {
        console.error('Error initializing chatbot:', error);
        throw error;
    }
}

module.exports = { initializeChatbot }; 