#!/usr/bin/env python3

import asyncio
from app.chatbot.initializer import initialize_chatbot

async def debug_model():
    print("Initializing chatbot...")
    processor = await initialize_chatbot()
    
    test_messages = [
        'when was RHCP formed',
        'name some of their songs'
    ]
    
    print("\n=== Testing Failing Cases ===")
    for message in test_messages:
        print(f"\nMessage: '{message}'")
        classifications = processor.get_classifications(message)
        print(f"Top 5 classifications:")
        for i, classification in enumerate(classifications[:5]):
            print(f"  {i+1}. {classification['label']}: {classification['value']:.4f}")
        
        response = processor.process_message(message)
        print(f"Final intent: {response['intent']}")
        print(f"Confidence: {response['confidence']:.4f}")

if __name__ == "__main__":
    asyncio.run(debug_model()) 