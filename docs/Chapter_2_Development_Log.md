# Chapter 2: Development Log

This chapter chronicles the key development activities, decisions, and milestones encountered during the RHCP Chatbot project. It serves as a historical record of the iterative progress.

## 2.1 Entry: 2023-10-27 (Recap of Progress to Date)

**Objective:** Summarize key development milestones and the current state of the RHCP Chatbot project.

**Tasks Completed:**

*   **Initial Setup & Refactoring:**
    *   Established an Express.js server (`src/app.js`).
    *   Loaded training data (`base-corpus.json`, `rhcp-corpus.json`) and static data (`band-info.json`, `discography.json`).
    *   Implemented initial NLU using `natural.BayesClassifier`, subsequently transitioning to `natural.LogisticRegressionClassifier`.
    *   Created `ChatbotProcessor` for core message handling.
    *   Refactored the application into a modular structure:
        *   `src/initializer.js`: Manages data loading, classifier training, and `ChatbotProcessor` instantiation.
        *   `src/http/controllers/chatController.js`: Orchestrates message processing.
        *   `src/http/routes/chatRoutes.js`: Defines the `/api/chat` Express route.
        *   `src/app.js`: Focuses on server setup, delegating initialization and routing.
*   **NLU Tuning Attempts:**
    *   Refined utterances in `rhcp-corpus.json` to improve discrimination between `band.members` and `member.biography` intents.
    *   Implemented a confidence threshold in `chatbotProcessor.js` (experiments conducted with values of 0.6 and 0.8).
    *   Switched the classifier from `natural.BayesClassifier` to `natural.LogisticRegressionClassifier`.
    *   Observed persistent misclassifications for specific queries (e.g., "Who are the members of the band?", out-of-scope queries) despite these modifications.
*   **Automated Testing Framework (Initiation of Phase 5):**
    *   Installed Jest as a development dependency.
    *   Added a "test" script to `package.json`.
    *   Created `test/chatbotProcessor.test.js` with initial test cases.
    *   Test failures for problematic queries corroborated NLU limitations.
    *   Modified `chatbotProcessor.js` to log detailed classification information when `NODE_ENV=test` to facilitate better analysis.
*   **System Documentation:**
    *   Generated `SYSTEM_OVERVIEW.md` detailing system architecture and workflow. (Note: This file was later reported as deleted and may require regeneration or status confirmation).

**Current Status & Next Steps:**
The project is currently addressing challenges related to the NLU component's accuracy for certain query types. The immediate priority, as detailed in the `REFINED_IMPLEMENTATION_PLAN.md` (refer to Chapter 3), is **Phase 2A: NLU Enhancement & Iterative Testing**.

---

## 2.2 Entry: 2023-10-27 (Current Task Execution)

**Phase:** 2A - NLU Enhancement & Iterative Testing

**Objective:** Systematically address current NLU misclassifications and significantly improve overall NLU accuracy, robustness, and out-of-scope detection.

**Sub-Task (2A.1): Training Data Augmentation & Refinement**
*   **Action:** Initiated a comprehensive review of `rhcp-corpus.json` and `base-corpus.json` to identify and rectify ambiguities, overlaps, and gaps, with particular attention to problematic intents such as `band.members`, `member.biography`, and `greetings.hello`.
*   **Update (2023-10-27):**
    *   Refined utterances for the `member.biography` intent in `src/data/training/rhcp-corpus.json` by removing ambiguous phrases and incorporating more specific examples.
    *   Augmented `greetings.hello` and `intent.outofscope` in `src/data/training/base-corpus.json` with additional, diverse utterances.
    *   Re-executed Jest automated tests (`npm test` with `NODE_ENV=test`).
    *   **All tests passed.** Significant improvements were observed in classification logs:
        *   "Hello": Correctly classified as `greetings.hello` with a confidence of **0.9818** (previously 0.585, below the threshold).
        *   "Who are the members of the band?": Correctly classified as `band.members` with a confidence of **0.9963** (previously misclassified as `member.biography`).
        *   "Tell me about quantum physics": Correctly classified as `intent.outofscope` with a confidence of **0.9977** (previously misclassified as `agent.acquaintance`).
    *   This NLU refinement notably improved accuracy for previously problematic queries.

**Next Sub-Task (2A.2): Commit NLU Improvements & Iteration**
*   **Action:** Commit the successful NLU changes to the version control repository.
*   **Update (2023-10-27):** Changes were committed and pushed successfully.

---

## 2.3 Entry: 2023-10-27 (Continuing Phase 2A)

**Phase:** 2A - NLU Enhancement & Iterative Testing

**Objective:** Continue to systematically address NLU misclassifications and enhance overall accuracy, robustness, and out-of-scope detection.

**Sub-Task (2A.2 continued): Advanced NLU Techniques Exploration & Implementation**
*   **Action:** Experimented with preprocessing techniques, specifically stop-word removal.
    *   Modified `src/initializer.js` to tokenize utterances and remove English stop words prior to training the `LogisticRegressionClassifier`.
    *   Re-executed Jest automated tests (`npm test` with `NODE_ENV=test`).
    *   **Test Results:** Three tests failed (related to `band.members`, `album.info`, `song.info`). Analysis of classification logs indicated that stop-word removal introduced regressions, likely by eliminating important contextual words, leading to misclassifications for previously correct intents.
    *   **Decision:** Reverted the stop-word removal changes in `src/initializer.js` due to its detrimental impact on NLU accuracy for this specific setup.
    *   Re-ran tests post-revert: All 8 tests passed, confirming the restoration of the previous NLU performance level.
*   **Next Action (Phase 2A.2):** Investigate other aspects of `natural.LogisticRegressionClassifier` tuning or explore alternative NLU libraries and techniques. 