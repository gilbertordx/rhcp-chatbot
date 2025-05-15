/**
 * Handles the processing of user messages for the RHCP Chatbot.
 * Performs intent recognition, entity extraction, and response generation.
 */
class ChatbotProcessor {
    constructor(classifier, trainingData, staticData) {
        this.classifier = classifier;
        this.trainingData = trainingData;
        this.staticData = staticData;

        // Prepare entities for extraction (simple dictionary lookup) - moved from RHCPChatbot
        this.knownMembers = this.staticData.bandInfo.currentMembers
            .map(member => member.name.toLowerCase())
            .concat(this.staticData.bandInfo.formerMembers.map(member => member.name.toLowerCase()));
        this.knownAlbums = this.staticData.discography.studioAlbums
            .map(album => album.name.toLowerCase())
            .concat(this.staticData.discography.compilationAlbums.map(album => album.name.toLowerCase()))
            .concat(this.staticData.discography.liveAlbums.map(album => album.name.toLowerCase()));
        // Extract all track titles from all albums
        this.knownSongs = this.staticData.discography.studioAlbums.reduce((acc, album) => {
            return acc.concat(album.tracks.map(track => track.toLowerCase()));
        }, []);

        // --- Temporary Log for Debugging ---
        // console.log('Known Members for Entity Extraction:', this.knownMembers);
        // -----------------------------------

        // Train the classifier
    }

    async processMessage(message) {
        const cleanMessage = message.toLowerCase();

        // Intent recognition
        const intent = this.classifier.classify(cleanMessage);

        // Entity extraction (simple dictionary lookup)
        const entities = [];

        // Extract members
        for (const member of this.knownMembers) {
            if (cleanMessage.includes(member)) {
                entities.push({ type: 'member', value: this.staticData.bandInfo.currentMembers.find(m => m.name.toLowerCase() === member) || this.staticData.bandInfo.formerMembers.find(m => m.name.toLowerCase() === member) });
            }
        }

        // Extract albums
        for (const album of this.knownAlbums) {
            if (cleanMessage.includes(album)) {
                entities.push({ type: 'album', value: this.staticData.discography.studioAlbums.find(a => a.name.toLowerCase() === album) || this.staticData.discography.compilationAlbums.find(a => a.name.toLowerCase() === album) || this.staticData.discography.liveAlbums.find(a => a.name.toLowerCase() === album) });
            }
        }

        // Extract songs
        for (const song of this.knownSongs) {
            if (cleanMessage.includes(song)) {
                 // Find the song object. This requires searching through all albums.
                let songDetails = null;
                for (const albumType of ['studioAlbums', 'compilationAlbums', 'liveAlbums']) {
                    for (const album of this.staticData.discography[albumType]) {
                        if (album.tracks && album.tracks.map(t => t.toLowerCase()).includes(song)) {
                            songDetails = { name: song, album: album.name };
                            break;
                        }
                    }
                    if (songDetails) break;
                }
                 if (songDetails) {
                    entities.push({ type: 'song', value: songDetails });
                } else {
                     // Fallback if song is found but not in a listed tracklist (e.g., a single not on an album list)
                     entities.push({ type: 'song', value: { name: song } });
                }
            }
        }

        // Simple Response Generation based on Intent and Entities
        let responseMessage = "Sorry, I didn't understand that.";
        let foundIntentData = null;

        // Prioritize specific responses based on intent and entities
        if (intent === 'member.biography' && entities.find(e => e.type === 'member')) {
            const memberEntity = entities.find(e => e.type === 'member').value;
            if (memberEntity && memberEntity.biography) {
                responseMessage = `${memberEntity.name}: ${memberEntity.biography}`;
            } else if (memberEntity) {
                 responseMessage = `I know about ${memberEntity.name}, but I don't have a detailed biography for them at the moment.`;
            }
        } else if (intent === 'album.specific' && entities.find(e => e.type === 'album')) {
             const albumEntity = entities.find(e => e.type === 'album').value;
             if (albumEntity) {
                 let albumInfo = `${albumEntity.name} was released on ${albumEntity.releaseDate}`;
                 if (albumEntity.producer) albumInfo += ` and produced by ${albumEntity.producer}`;
                 if (albumEntity.tracks) albumInfo += `. It includes tracks like ${albumEntity.tracks.slice(0, 5).join(', ')}${albumEntity.tracks.length > 5 ? '...' : ''}.`;
                 responseMessage = albumInfo;
             } else {
                 responseMessage = `I know about that album, but I don't have specific details right now.`;
             }
         } else if ((intent === 'album.specific' || intent === 'song.specific') && entities.find(e => e.type === 'song')) {
             // Handle queries asking about a song, potentially classified as album or song specific
             const songEntity = entities.find(e => e.type === 'song').value;
             if (songEntity && songEntity.album) {
                 responseMessage = `${songEntity.name} is from the album ${songEntity.album}.`;
             } else if (songEntity) {
                 responseMessage = `I know the song ${songEntity.name}, but I'm not sure which album it's on.`;
             } else {
                 responseMessage = `I know about songs, but I couldn't find details for the one you mentioned.`;
             }
         } else if (intent === 'song.specific' && entities.find(e => e.type === 'song')) {
             const songEntity = entities.find(e => e.type === 'song').value;
             if (songEntity && songEntity.album) {
                 responseMessage = `${songEntity.name} is a song from the album ${songEntity.album}.`;
             } else if (songEntity) {
                 responseMessage = `I know the song ${songEntity.name}.`;
             } else {
                 responseMessage = `I know that song, but I don't have specific details right now.`;
             }
        } else {
            // Fallback to general intent answers if no specific entity response is generated
            for (const corpus of [this.trainingData.base, this.trainingData.rhcp]) {
                foundIntentData = corpus.data.find(item => item.intent === intent);
                if (foundIntentData && foundIntentData.answers && foundIntentData.answers.length > 0) {
                    const randomIndex = Math.floor(Math.random() * foundIntentData.answers.length);
                    responseMessage = foundIntentData.answers[randomIndex];
                    break;
                }
            }
        }

        return {
            message: responseMessage,
            intent: intent,
            entities: entities
        };
    }
}

module.exports = ChatbotProcessor; 