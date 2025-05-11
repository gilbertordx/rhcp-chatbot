'use strict';

module.exports = {
  up: async (queryInterface, Sequelize) => {
    // First, insert the knowledge base data
    const knowledgeData = [
      {
        type: 'band_member',
        title: 'Anthony Kiedis',
        content: JSON.stringify({
          role: 'Lead Vocalist',
          joined: '1983',
          biography: 'Anthony Kiedis is the lead vocalist and founding member of the Red Hot Chili Peppers. Known for his distinctive vocal style and energetic performances.',
          contributions: ['Songwriting', 'Lyrics', 'Stage Performance']
        }),
        metadata: JSON.stringify({
          birthDate: '1962-11-01',
          birthplace: 'Grand Rapids, Michigan',
          instruments: ['Vocals']
        }),
        tags: ['vocalist', 'founder', 'frontman'],
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        type: 'band_member',
        title: 'Flea',
        content: JSON.stringify({
          role: 'Bassist',
          joined: '1983',
          biography: 'Flea is the bassist and founding member of the Red Hot Chili Peppers. Known for his distinctive slap bass technique and energetic stage presence.',
          contributions: ['Bass', 'Backing Vocals', 'Trumpet']
        }),
        metadata: JSON.stringify({
          birthDate: '1962-10-16',
          birthplace: 'Melbourne, Australia',
          instruments: ['Bass', 'Trumpet', 'Piano']
        }),
        tags: ['bassist', 'founder', 'musician'],
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        type: 'band_member',
        title: 'John Frusciante',
        content: JSON.stringify({
          role: 'Guitarist',
          joined: '1988',
          biography: 'John Frusciante is the guitarist of the Red Hot Chili Peppers. Known for his unique playing style and melodic approach to guitar.',
          contributions: ['Guitar', 'Backing Vocals', 'Songwriting']
        }),
        metadata: JSON.stringify({
          birthDate: '1970-03-05',
          birthplace: 'New York City, New York',
          instruments: ['Guitar', 'Vocals', 'Synthesizer']
        }),
        tags: ['guitarist', 'musician', 'songwriter'],
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        type: 'band_member',
        title: 'Chad Smith',
        content: JSON.stringify({
          role: 'Drummer',
          joined: '1988',
          biography: 'Chad Smith is the drummer of the Red Hot Chili Peppers. Known for his powerful and precise drumming style.',
          contributions: ['Drums', 'Percussion']
        }),
        metadata: JSON.stringify({
          birthDate: '1961-10-25',
          birthplace: 'Saint Paul, Minnesota',
          instruments: ['Drums', 'Percussion']
        }),
        tags: ['drummer', 'musician'],
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        type: 'album',
        title: 'Blood Sugar Sex Magik',
        content: JSON.stringify({
          releaseDate: '1991-09-24',
          producer: 'Rick Rubin',
          label: 'Warner Bros. Records',
          description: 'The band\'s breakthrough album that brought them mainstream success.',
          tracklist: [
            'The Power of Equality',
            'If You Have to Ask',
            'Breaking the Girl',
            'Funky Monks',
            'Suck My Kiss',
            'I Could Have Lied',
            'Mellowship Slinky in B Major',
            'The Righteous & the Wicked',
            'Give It Away',
            'Blood Sugar Sex Magik',
            'Under the Bridge',
            'Naked in the Rain',
            'Apache Rose Peacock',
            'The Greeting Song',
            'My Lovely Man',
            'Sir Psycho Sexy',
            'They\'re Red Hot'
          ]
        }),
        metadata: JSON.stringify({
          duration: '73:55',
          genre: ['Funk Rock', 'Alternative Rock'],
          sales: 'Over 13 million copies worldwide'
        }),
        tags: ['classic', 'breakthrough', '1991'],
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        type: 'song',
        title: 'Under the Bridge',
        content: JSON.stringify({
          album: 'Blood Sugar Sex Magik',
          releaseDate: '1992-03-10',
          writer: ['Anthony Kiedis', 'Flea', 'John Frusciante', 'Chad Smith'],
          description: 'A deeply personal song about Kiedis\'s struggles with drug addiction and loneliness in Los Angeles.',
          lyrics: 'Sometimes I feel like I don\'t have a partner...'
        }),
        metadata: JSON.stringify({
          duration: '4:24',
          genre: ['Alternative Rock', 'Ballad'],
          awards: ['MTV Video Music Award for Best Alternative Video']
        }),
        tags: ['ballad', 'acoustic', 'emotional'],
        createdAt: new Date(),
        updatedAt: new Date()
      }
    ];

    await queryInterface.bulkInsert('rhcp_knowledge', knowledgeData, {});

    // Then, insert the corpus data
    const corpusData = [
      {
        type: 'qa',
        title: 'Band Members Question',
        content: JSON.stringify({
          question: 'Who are the current members of Red Hot Chili Peppers?',
          answer: 'The current members of Red Hot Chili Peppers are Anthony Kiedis (vocals), Flea (bass), John Frusciante (guitar), and Chad Smith (drums).'
        }),
        metadata: JSON.stringify({
          category: 'band_info',
          confidence: 0.95
        }),
        tags: ['members', 'current', 'band'],
        createdAt: new Date(),
        updatedAt: new Date()
      }
    ];

    await queryInterface.bulkInsert('rhcp_knowledge', corpusData, {});
  },

  down: async (queryInterface, Sequelize) => {
    await queryInterface.bulkDelete('rhcp_knowledge', null, {});
  }
}; 