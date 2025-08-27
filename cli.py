#!/usr/bin/env python3
"""
RHCP Chatbot CLI

A command-line interface for the Red Hot Chili Peppers chatbot.
"""

import argparse
import asyncio
import json
import sys
from typing import Any

from app.chatbot.initializer import initialize_chatbot
from app.chatbot.memory import ConversationMemory
from app.config import get_settings
from app.core.inference import initialize_inference, run_inference
from app.errors import InvalidInputError
from app.infra.logging import get_logger, setup_logging


class RHCPChatbotCLI:
    """Command-line interface for the RHCP chatbot."""

    def __init__(
        self,
        api_url: str | None = None,
        use_api: bool = False,
        debug: bool = False,
        json_output: bool = False,
    ):
        """Initialize the CLI."""
        self.api_url = api_url
        self.use_api = use_api
        self.debug = debug
        self.json_output = json_output
        self.chatbot_processor = None
        self.memory_manager = None
        self.session_id = None
        self.auth_token = None
        self.logger = get_logger(__name__)

        # Command routing - these commands bypass NLU
        self.commands = {
            "help": self._show_help,
            "history": self._show_history,
            "quit": self._quit_session,
            "exit": self._quit_session,
            "bye": self._quit_session,
            "commands": self._show_commands,
        }

    async def initialize(self):
        """Initialize the chatbot processor."""
        if self.use_api:
            self.logger.info("Using API mode")
            return

        self.logger.info("Initializing local chatbot processor...")
        self.chatbot_processor = await initialize_chatbot()
        self.memory_manager = ConversationMemory(
            max_sessions=10, session_timeout_hours=1
        )
        self.session_id = self.memory_manager.create_session()

        # Initialize inference pipeline
        initialize_inference(self.chatbot_processor, self.memory_manager)

        self.logger.info("Chatbot initialized successfully")

    async def authenticate(self):
        """Authenticate with the API if using API mode."""
        if not self.use_api:
            return

        # TODO: Implement API authentication
        self.logger.info("API authentication not yet implemented")

    def send_message(self, message: str) -> dict[str, Any]:
        """Send a message and get a response."""
        # Input validation
        if not message or not message.strip():
            raise InvalidInputError("Message cannot be empty or whitespace")

        message = message.strip()
        if len(message) > 2000:
            raise InvalidInputError("Message too long (max 2000 characters)")

        # Command routing - check if this is a CLI command
        command = message.lower()
        if command in self.commands:
            return self.commands[command]()

        self.logger.info(
            f"Processing message: {message[:50]}{'...' if len(message) > 50 else ''}"
        )

        if self.use_api:
            return self._send_message_api(message)
        else:
            return self._send_message_local(message)

    def _send_message_local(self, message: str) -> dict[str, Any]:
        """Send message via local processor using unified inference pipeline."""
        if not self.chatbot_processor:
            raise RuntimeError("Chatbot processor not initialized")

        # Use unified inference pipeline
        response = run_inference(message, self.session_id)

        # Convert to dict for CLI compatibility
        result = response.model_dump()

        # Add CLI-specific fields
        result["message"] = result["final_message"]  # For backward compatibility
        result["intent"] = result["intent"]
        result["confidence"] = result["confidence"]
        result["entities"] = [e.dict() for e in result["entities"]]

        # Debug mode: show top-3 intents and probabilities
        if self.debug:
            classifications = self.chatbot_processor.get_classifications(
                message.lower()
            )
            if classifications:
                self.logger.info(
                    "┌─────────────────────────────────────────────────────────────┐"
                )
                self.logger.info(
                    "│                    Top 3 Intents                            │"
                )
                self.logger.info(
                    "├─────────────────────────────────────────────────────────────┤"
                )
                for i, classification in enumerate(classifications[:3], 1):
                    label = classification["label"]
                    value = classification["value"]
                    self.logger.info(f"│ {i}. {label:<30} {value:.3f} │")
                self.logger.info(
                    "└─────────────────────────────────────────────────────────────┘"
                )

        return result

    def _send_message_api(self, message: str) -> dict[str, Any]:
        """Send message via API."""
        # TODO: Implement API communication
        self.logger.info("API mode not yet implemented")
        return {
            "message": "API mode not yet implemented",
            "intent": "unknown",
            "confidence": 0.0,
            "entities": [],
        }

    def _show_help(self) -> dict[str, Any]:
        """Show help information."""
        help_text = """
RHCP Chatbot Help
=================

This chatbot can answer questions about the Red Hot Chili Peppers, including:
- Band members and their biographies
- Albums and their details
- Songs and their information
- Band history and formation

Commands:
- help: Show this help message
- history: Show conversation history
- commands: List available commands
- quit/exit/bye: End the session

Examples:
- "Who is in the band?"
- "Tell me about Californication"
- "What year was RHCP formed?"
- "Who wrote Under the Bridge?"
        """.strip()

        return {
            "message": help_text,
            "intent": "command.help",
            "confidence": 1.0,
            "entities": [],
        }

    def _show_history(self) -> dict[str, Any]:
        """Show conversation history."""
        if not self.memory_manager or not self.session_id:
            return {
                "message": "No conversation history available.",
                "intent": "command.history",
                "confidence": 1.0,
                "entities": [],
            }

        history = self.memory_manager.get_conversation_history(
            self.session_id, max_messages=10
        )

        if not history:
            return {
                "message": "No conversation history yet.",
                "intent": "command.history",
                "confidence": 1.0,
                "entities": [],
            }

        history_text = "Conversation History:\n"
        for i, entry in enumerate(history[-10:], 1):  # Last 10 messages
            user_msg = entry.get("user_message", "")
            bot_msg = entry.get("bot_message", "")
            intent = entry.get("intent", "unknown")
            conf = entry.get("confidence", 0.0)

            history_text += f"\nTurn {i}:\n"
            history_text += f"  You: {user_msg}\n"
            history_text += f"  Bot: {bot_msg}\n"
            history_text += f"  Intent: {intent} ({conf:.3f})\n"

        return {
            "message": history_text,
            "intent": "command.history",
            "confidence": 1.0,
            "entities": [],
        }

    def _quit_session(self) -> dict[str, Any]:
        """Quit the session."""
        return {
            "message": "Goodbye! Thanks for chatting about RHCP. Come back anytime!",
            "intent": "command.quit",
            "confidence": 1.0,
            "entities": [],
        }

    def _show_commands(self) -> dict[str, Any]:
        """Show available commands."""
        commands_text = """
Available Commands:
==================
- help: Show help information
- history: Show conversation history
- commands: List available commands
- quit/exit/bye: End the session

You can also ask questions about RHCP members, albums, songs, and history!
        """.strip()

        return {
            "message": commands_text,
            "intent": "command.list",
            "confidence": 1.0,
            "entities": [],
        }

    def print_response(self, response: dict[str, Any]):
        """Print the response in the appropriate format."""
        if self.json_output:
            # Print JSON response
            print(json.dumps(response, indent=2))
        else:
            # Print human-readable response
            print(f"\n{response['message']}")

            if self.debug:
                print(
                    f"\n[DEBUG] Intent: {response['intent']} (confidence: {response['confidence']:.3f})"
                )
                if response.get("entities"):
                    print(f"[DEBUG] Entities: {len(response['entities'])} found")
                    for entity in response["entities"]:
                        print(
                            f"  - {entity.get('type', 'unknown')}: {entity.get('value', {}).get('name', 'unknown')}"
                        )


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="RHCP Chatbot CLI")
    parser.add_argument("--message", "-m", help="Send a single message and exit")
    parser.add_argument("--api-url", help="API URL for remote mode")
    parser.add_argument(
        "--use-api",
        action="store_true",
        help="Use API mode instead of local processing",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--json", action="store_true", help="Output responses in JSON format"
    )

    args = parser.parse_args()

    # Setup logging
    settings = get_settings()
    setup_logging(
        level="DEBUG" if args.debug else settings.log_level,
        format_type=settings.log_format,
        debug=args.debug,
    )

    # Create CLI instance
    cli = RHCPChatbotCLI(
        api_url=args.api_url,
        use_api=args.use_api,
        debug=args.debug,
        json_output=args.json,
    )

    try:
        # Initialize
        await cli.initialize()
        await cli.authenticate()

        if args.message:
            # Single message mode
            try:
                response = cli.send_message(args.message)
                cli.print_response(response)
            except InvalidInputError as e:
                print(f"Error: {e.message}")
                sys.exit(1)
        else:
            # Interactive mode
            print("RHCP Chatbot CLI")
            print("Type 'help' for commands, 'quit' to exit")
            print("=" * 50)

            while True:
                try:
                    user_input = input("\nYou: ").strip()
                    if not user_input:
                        continue

                    response = cli.send_message(user_input)
                    cli.print_response(response)

                    # Check if user wants to quit
                    if response.get("intent") == "command.quit":
                        break

                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break
                except InvalidInputError as e:
                    print(f"Error: {e.message}")
                except Exception as e:
                    print(f"Unexpected error: {e}")
                    if args.debug:
                        import traceback

                        traceback.print_exc()

    except Exception as e:
        print(f"Failed to initialize chatbot: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
