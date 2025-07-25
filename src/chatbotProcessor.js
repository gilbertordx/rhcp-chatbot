// const CONFIDENCE_THRESHOLD = 0.6; // Original threshold
const CONFIDENCE_THRESHOLD = 0.0005; // Temporarily lowered for BayesClassifier testing

class ChatbotProcessor {
    constructor(classifier, trainingData, staticData) {
        this.classifier = classifier;
        this.trainingData = trainingData;
        this.staticData = staticData;

        this.knownMembers = this.staticData.bandInfo.currentMembers
            .map(member => member.name.toLowerCase())
            .concat(this.staticData.bandInfo.formerMembers.map(member => member.name.toLowerCase()));
        this.knownAlbums = this.staticData.discography.studioAlbums
            .map(album => album.name.toLowerCase())
            .concat(this.staticData.discography.compilationAlbums.map(album => album.name.toLowerCase()))
            .concat(this.staticData.discography.liveAlbums.map(album => album.name.toLowerCase()));
        this.knownSongs = [];
        for (const albumType of ['studioAlbums', 'compilationAlbums', 'liveAlbums']) {
            for (const album of this.staticData.discography[albumType]) {
                if (album.tracks && Array.isArray(album.tracks)) {
                    album.tracks.forEach(track => {
                        this.knownSongs.push({ 
                            name: track.toLowerCase(), 
                            album: album.name 
                        });
                    });
                }
            }
        }
    }

    async processMessage(message) {
        const cleanMessage = message.toLowerCase();

        const classifications = this.classifier.getClassifications(cleanMessage);
        let intent = 'None';
        let confidence = 0;

        if (process.env.NODE_ENV === 'test') {
            console.log('Message:', message);
            console.log('Classifications:', classifications);
        }

        if (classifications && classifications.length > 0) {
            const topClassification = classifications[0];

            if (topClassification.value > CONFIDENCE_THRESHOLD) {
                intent = topClassification.label;
                confidence = topClassification.value;
            } else {
                intent = 'unrecognized';
            }
        } else {
            intent = 'unrecognized';
        }

        const entities = [];

        for (const member of this.knownMembers) {
            if (cleanMessage.includes(member)) {
                entities.push({ type: 'member', value: this.staticData.bandInfo.currentMembers.find(m => m.name.toLowerCase() === member) || this.staticData.bandInfo.formerMembers.find(m => m.name.toLowerCase() === member) });
            }
        }

        for (const album of this.knownAlbums) {
            if (cleanMessage.includes(album)) {
                entities.push({ type: 'album', value: this.staticData.discography.studioAlbums.find(a => a.name.toLowerCase() === album) || this.staticData.discography.compilationAlbums.find(a => a.name.toLowerCase() === album) || this.staticData.discography.liveAlbums.find(a => a.name.toLowerCase() === album) });
            }
        }

        for (const songInfo of this.knownSongs) {
            if (cleanMessage.includes(songInfo.name)) {
                entities.push({ type: 'song', value: { name: songInfo.name, album: songInfo.album } });
            }
        }

        let responseMessage = "";
        let handledBySpecificLogic = false;

        if (intent === 'unrecognized' || intent === 'None') {
            responseMessage = "Sorry, I didn't understand that.";
            handledBySpecificLogic = true; 
        } else if (intent === 'member.biography' && entities.find(e => e.type === 'member')) {
            const memberEntity = entities.find(e => e.type === 'member').value;
            if (memberEntity && memberEntity.biography) {
                responseMessage = `${memberEntity.name}: ${memberEntity.biography}`;
            } else if (memberEntity) {
                responseMessage = `I know about ${memberEntity.name}, but I don't have a detailed biography for them at the moment.`;
            }
            handledBySpecificLogic = true;
        } else if (intent === 'album.specific' && entities.find(e => e.type === 'album')) {
            const albumEntity = entities.find(e => e.type === 'album').value;
            if (albumEntity) {
                let albumInfo = `${albumEntity.name} was released on ${albumEntity.releaseDate}`;
                if (albumEntity.producer) albumInfo += ` and produced by ${albumEntity.producer}`;
                if (albumEntity.tracks) albumInfo += `. It includes tracks like ${albumEntity.tracks.slice(0, 5).join(', ')}${albumEntity.tracks.length > 5 ? '...' : ''}.`;
                responseMessage = albumInfo;
            }
            handledBySpecificLogic = true;
        } else if ((intent === 'album.specific' || intent === 'song.specific') && entities.find(e => e.type === 'song')) {
            const songEntity = entities.find(e => e.type === 'song').value;
            if (songEntity && songEntity.album) {
                responseMessage = `${songEntity.name} is from the album ${songEntity.album}. You can ask for more details about the song or the album specifically.`;
            } else if (songEntity) {
                responseMessage = `I know the song ${songEntity.name}. You can ask for more details about it.`;
            }
            handledBySpecificLogic = true;
        } else if (intent === 'song.specific' && entities.find(e => e.type === 'song')) {
            const songEntity = entities.find(e => e.type === 'song').value;
            if (songEntity && songEntity.album) {
                responseMessage = `${songEntity.name} is a song from the album ${songEntity.album}.`;
            } else if (songEntity) {
                responseMessage = `I know the song ${songEntity.name}.`;
            }
            handledBySpecificLogic = true;
        }

        if (!handledBySpecificLogic && intent !== 'unrecognized' && intent !== 'None') {
            let foundIntentData = null;
            for (const corpus of [this.trainingData.base, this.trainingData.rhcp]) {
                foundIntentData = corpus.data.find(item => item.intent === intent);
                if (foundIntentData && foundIntentData.answers && foundIntentData.answers.length > 0) {
                    const randomIndex = Math.floor(Math.random() * foundIntentData.answers.length);
                    responseMessage = foundIntentData.answers[randomIndex];
                    break;
                }
            }
            if (!responseMessage) {
                responseMessage = `I understood your intent is '${intent}', but I don't have a specific response for that yet.`;
            }
        }
        
        if (!responseMessage) {
             responseMessage = "Sorry, I couldn't process your request.";
        }

        return {
            message: responseMessage,
            intent: intent,
            confidence: confidence,
            entities: entities,
            classifications: classifications
        };
    }
}

module.exports = ChatbotProcessor; 