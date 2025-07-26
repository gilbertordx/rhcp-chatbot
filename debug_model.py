#!/usr/bin/env python3

import asyncio
from app.chatbot.initializer import initialize_chatbot

async def debug_model():
    print("Initializing chatbot...")
    processor = await initialize_chatbot()
    
    test_messages = [
        # Member tests
        'tell me about anthony kiedis',
        'who is flea',
        'john frusciante biography',
        'chad smith info',
        'hillel slovak',
        
        # Album tests
        'californication album',
        'blood sugar sex magik',
        'unlimited love',
        'stadium arcadium',
        
        # Song tests
        'under the bridge',
        'scar tissue',
        'give it away',
        'black summer',
        
        # Mixed tests
        'what songs are on californication',
        'who sings under the bridge',
        'when was blood sugar sex magik released'
    ]
    
    print("\n=== Testing Enhanced Entity Recognition ===")
    for message in test_messages:
        print(f"\nMessage: '{message}'")
        response = processor.process_message(message)
        print(f"Intent: {response['intent']}")
        print(f"Confidence: {response['confidence']:.4f}")
        print(f"Entities found: {len(response['entities'])}")
        for entity in response['entities']:
            print(f"  - Type: {entity['type']}")
            if entity['type'] == 'member':
                print(f"    Member: {entity['value']['name']} ({entity.get('member_type', 'unknown')})")
            elif entity['type'] == 'album':
                print(f"    Album: {entity['value']['name']} ({entity.get('album_type', 'unknown')})")
            elif entity['type'] == 'song':
                print(f"    Song: {entity['value']['name']} (from {entity['value']['album']})")
        print(f"Response: {response['message'][:100]}{'...' if len(response['message']) > 100 else ''}")

if __name__ == "__main__":
    asyncio.run(debug_model()) 