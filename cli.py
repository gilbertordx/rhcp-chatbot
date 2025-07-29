#!/usr/bin/env python3
"""
RHCP Chatbot CLI Tool

A command-line interface for interacting with the RHCP chatbot.
Supports both local processing and API communication.
"""

import argparse
import asyncio
import json
import sys
from typing import Optional, Dict, Any
import requests
from app.chatbot.initializer import initialize_chatbot
from app.chatbot.memory import ConversationMemory


class RHCPChatbotCLI:
    def __init__(self, api_url: Optional[str] = None, use_api: bool = False):
        self.api_url = api_url or "http://localhost:8000"
        self.use_api = use_api
        self.chatbot_processor = None
        self.memory_manager = None
        self.session_id = None
        self.auth_token = None
        
    async def initialize(self):
        """Initialize the chatbot processor."""
        if not self.use_api:
            print("Initializing local chatbot...")
            self.chatbot_processor = await initialize_chatbot()
            self.memory_manager = ConversationMemory(max_sessions=10, session_timeout_hours=1)
            self.session_id = self.memory_manager.create_session()
            print("Local chatbot initialized successfully!")
        else:
            print("Using API mode - no local initialization needed")
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with the API."""
        if not self.use_api:
            return True
            
        try:
            response = requests.post(
                f"{self.api_url}/api/auth/login",
                json={"username": username, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data["access_token"]
                print(f"Authenticated as {username}")
            else:
                print(f"Authentication failed: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
        
        return self.auth_token is not None
    
    def send_message(self, message: str) -> Dict[str, Any]:
        """Send a message and get response."""
        if self.use_api:
            return self._send_message_api(message)
        else:
            return self._send_message_local(message)
    
    def _send_message_api(self, message: str) -> Dict[str, Any]:
        """Send message via API."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        data = {"message": message}
        if self.session_id:
            data["session_id"] = self.session_id
        
        try:
            response = requests.post(
                f"{self.api_url}/api/chat",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "message": f"API Error: {response.status_code} - {response.text}",
                    "intent": "error",
                    "confidence": 0.0,
                    "entities": []
                }
        except requests.exceptions.RequestException as e:
            return {
                "message": f"Connection Error: {e}",
                "intent": "error",
                "confidence": 0.0,
                "entities": []
            }
    
    def _send_message_local(self, message: str) -> Dict[str, Any]:
        """Send message using local processor."""
        if not self.chatbot_processor:
            return {
                "message": "Chatbot not initialized",
                "intent": "error",
                "confidence": 0.0,
                "entities": []
            }
        
        return self.chatbot_processor.process_message(message, self.session_id)
    
    def get_history(self) -> list:
        """Get conversation history."""
        if not self.use_api:
            if self.memory_manager and self.session_id:
                return self.memory_manager.get_conversation_history(self.session_id)
            return []
        else:
            return self._get_history_api()
    
    def _get_history_api(self) -> list:
        """Get history via API."""
        if not self.auth_token or not self.session_id:
            return []
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = requests.get(
                f"{self.api_url}/api/chat/history/{self.session_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("history", [])
            else:
                return []
        except requests.exceptions.RequestException:
            return []
    
    def print_response(self, response: Dict[str, Any]):
        """Print a formatted response."""
        print(f"\n{response['message']}")
        print(f"Intent: {response['intent']} (confidence: {response.get('confidence', 0):.2f})")
        
        if response.get('entities'):
            print("Entities:")
            for entity in response['entities']:
                print(f"   - {entity['type']}: {entity['value'].get('name', entity['value'])}")
        
        print("-" * 50)
    
    def interactive_mode(self):
        """Run interactive chat mode."""
        print("\nWelcome to RHCP Chatbot CLI!")
        print("Type 'quit', 'exit', or 'bye' to end the conversation")
        print("Type 'history' to see conversation history")
        print("Type 'help' for available commands")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Goodbye! Thanks for chatting about RHCP!")
                    break
                
                if user_input.lower() == 'history':
                    history = self.get_history()
                    if history:
                        print("\nConversation History:")
                        for i, entry in enumerate(history[-5:], 1):  # Show last 5 messages
                            print(f"{i}. You: {entry['user_message']}")
                            print(f"   Bot: {entry['bot_response']['message'][:100]}...")
                    else:
                        print("No conversation history yet.")
                    continue
                
                if user_input.lower() == 'help':
                    print("\nAvailable Commands:")
                    print("  - Type any question about RHCP")
                    print("  - 'history' - Show conversation history")
                    print("  - 'quit', 'exit', 'bye' - End conversation")
                    print("  - 'help' - Show this help")
                    continue
                
                # Send message and get response
                response = self.send_message(user_input)
                self.print_response(response)
                
            except KeyboardInterrupt:
                print("\nGoodbye! Thanks for chatting about RHCP!")
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="RHCP Chatbot CLI Tool")
    parser.add_argument(
        "--api", 
        action="store_true", 
        help="Use API mode instead of local processing"
    )
    parser.add_argument(
        "--api-url", 
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--username", 
        help="Username for API authentication"
    )
    parser.add_argument(
        "--password", 
        help="Password for API authentication"
    )
    parser.add_argument(
        "--message", 
        help="Send a single message and exit"
    )
    parser.add_argument(
        "--json", 
        action="store_true", 
        help="Output response in JSON format"
    )
    
    args = parser.parse_args()
    
    # Create CLI instance
    cli = RHCPChatbotCLI(api_url=args.api_url, use_api=args.api)
    
    # Initialize
    asyncio.run(cli.initialize())
    
    # Authenticate if using API and credentials provided
    if args.api and args.username and args.password:
        if not cli.authenticate(args.username, args.password):
            sys.exit(1)
    
    # Single message mode
    if args.message:
        response = cli.send_message(args.message)
        if args.json:
            print(json.dumps(response, indent=2))
        else:
            cli.print_response(response)
        return
    
    # Interactive mode
    cli.interactive_mode()


if __name__ == "__main__":
    main() 