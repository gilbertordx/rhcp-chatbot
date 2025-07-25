# Chapter 1: System Architecture

This chapter provides a detailed explanation of the RHCP Chatbot application's architecture and core components as of the completion of Phase 1 of its initial implementation plan. The overview is intended to provide a foundational understanding of the system.

## 1.1 Natural Language Understanding (NLU)

The NLU module is central to interpreting user input.

*   **Implementation:** NLU functionality is primarily handled within the `src/chatbotProcessor.js` file.
*   **Core Logic:**
    *   Utilizes the `natural` Node.js library, specifically `natural.LogisticRegressionClassifier`, for intent classification.
    *   The classifier is trained by `src/initializer.js` using data from JSON files in `src/data/training/` (`base-corpus.json` and `rhcp-corpus.json`).
    *   Input messages undergo preprocessing (currently, lowercasing) before classification.
    *   The `processMessage` method in `chatbotProcessor.js` retrieves classification results, including confidence scores.
    *   A confidence threshold (currently 0.6) is applied; intents below this threshold are deemed 'unrecognized'.
*   **Current Status & Known Issues:**
    *   Entity extraction is rudimentary, relying on simple string matching against static data lists within `chatbotProcessor.js`.
    *   Initial testing revealed limitations:
        *   Ambiguity between similar intents (e.g., `band.members` vs. `member.biography`) can lead to misclassification, even with high confidence.
        *   The classifier may inaccurately assign high confidence to irrelevant intents for out-of-scope queries (e.g., classifying "quantum physics" as `agent.acquaintance`).
    *   The NLU component, in its current state, serves as a basic starting point and requires significant enhancement, as detailed in subsequent development phases.

## 1.2 Dialog Management

Dialog management governs the flow of conversation.

*   **Implementation:** This functionality is currently simple and integrated directly into the `processMessage` function in `src/chatbotProcessor.js`.
*   **Core Logic:**
    *   The system processes each user message in isolation, with no explicit state tracking.
    *   Responses are generated solely based on the classified intent and extracted entities from the *current* message.
    *   Conversation history, follow-up questions, and clarification of ambiguous input are not currently handled.
*   **Current Status & Known Issues:** This component is minimal. More sophisticated dialog management is necessary for multi-turn conversations or complex interactions, which are slated for future development.

## 1.3 Response Generation

This module is responsible for formulating the chatbot's replies.

*   **Implementation:** Response generation logic is located within the `processMessage` function in `src/chatbotProcessor.js`.
*   **Core Logic:**
    *   For recognized intents exceeding the confidence threshold, the system attempts to use specific logic (e.g., listing members from `static/band-info.json` for the `band.members` intent).
    *   If no specific handler exists or applies, or for recognized intents without a handler, the system defaults to selecting a random predefined answer associated with the classified intent from the loaded training corpus (`src/data/training/`).
    *   'Unrecognized' intents trigger a generic fallback message.
    *   Basic entity lookup (members, albums, songs) aids in tailoring some responses, though this integration is limited.
*   **Current Status & Known Issues:** Responses are often generic due to a heavy reliance on corpus fallback answers. Dynamic response generation using static data is implemented only for a few specific cases (e.g., `band.members`). The system does not yet handle missing or ambiguous entities during response generation.

## 1.4 Knowledge Base and Data Sources

The chatbot relies on a set of data sources for its information.

*   **Implementation:** Data is loaded from static JSON files located in the `src/data/` directory.
*   **Core Logic:**
    *   `src/data/training/` contains `base-corpus.json` and `rhcp-corpus.json`. These files store example utterances and predefined answers for NLU training and response fallback.
    *   `src/data/static/` contains `band-info.json` (member details) and `discography.json` (album and song details). These are loaded into memory and used for basic entity lookup and specific, albeit minimal, response generation logic.
*   **Current Status & Known Issues:** All data is currently loaded into memory from static files upon initialization. While simple, this approach is not scalable for large datasets. Phase 3 of the development plan includes database integration to manage larger and more structured data.

## 1.5 Application Programming Interface (API) and Interface

The API serves as the entry point for user interactions.

*   **Implementation:** The API is built using Express.js and is managed across `src/app.js`, `src/http/routes/chatRoutes.js`, and `src/http/controllers/chatController.js`.
*   **Core Logic:**
    *   `src/app.js` initializes the Express server and mounts the main router.
    *   `src/initializer.js` is invoked by `app.js` to load data and instantiate the `ChatbotProcessor` *before* the server begins listening for requests.
    *   `src/http/routes/chatRoutes.js` defines the `/api/chat` endpoint (mounted as `/` within the router).
    *   The route handler in `chatRoutes.js` calls the `processChatMessage` controller function in `src/http/controllers/chatController.js`. This function is passed the initialized `ChatbotProcessor` instance and the user's message, which is extracted from the request body.
    *   `src/http/controllers/chatController.js` acts as an intermediary, invoking `chatbotProcessor.processMessage` and formatting the response for API delivery.
*   **Current Status & Known Issues:** The API structure is established and functional for receiving messages and returning responses. Error handling is currently basic. The API response includes the generated message, classified intent, extracted entities, confidence score, and optionally, classification details (added for debugging). While this structure aligns with the interaction plan, it will require adaptation to accommodate more complex responses as dialog management and response generation capabilities evolve.

This architectural overview sets the stage for understanding the subsequent development efforts aimed at enhancing the NLU and response generation capabilities. 