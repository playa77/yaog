# YaOG (Yet Another OpenRouter GUI)

YaOG is a lightweight, feature-rich desktop client for the OpenRouter API, built with Python and PyQt6. It provides a robust interface for interacting with various LLMs, managing conversation history locally, and handling complex workflows like branching conversations and file analysis.

## Features

### Core Functionality
*   **OpenRouter Integration:** Connects to OpenRouter.ai to access a wide range of LLMs (commercial and open-source).
*   **Streaming Responses:** Real-time text generation with visual feedback.
*   **Local Storage:** All conversations and system prompts are stored locally in an SQLite database (~/.or-client/or-client.db).
*   **Markdown Rendering:** Full Markdown support with syntax highlighting for code blocks and table rendering.

### Conversation Management
*   **History:** Sidebar access to all past conversations, sorted by date.
*   **Branching & Editing:** Edit any user message to create a new branch from that point (pruning future messages).
*   **Pruning:** Delete a specific message and all subsequent messages to restart a conversation flow.
*   **Regeneration:** One-click regeneration of the last Assistant response.
*   **Import/Export:** Export conversations to JSON for backup or sharing; import them back into the application.

### Model & Prompt Management
*   **Custom Model List:** Manage your preferred models via a dedicated settings tab. Supports adding, editing, reordering, and deleting models.
*   **System Prompts:** Create, save, and manage reusable System Prompts (Personas). Inject them dynamically into new or existing chats.
*   **Capabilities:** Toggles for specific OpenRouter features like Web Search (:online) and Reasoning (include_reasoning).

### File Attachments & Context
*   **File Analysis:** Attach text-based files (code, logs, CSV, Markdown) and PDFs.
*   **Context Awareness:** The application extracts text from attachments and formats them for the LLM.
*   **Token Counting:** Real-time estimation of context token usage (requires tiktoken).

## Installation and Usage

### Running the Released Executable (Linux Only)
1.  Download the latest `YaOG` binary from the GitHub Releases page.
2.  Open your terminal and navigate to the directory where you downloaded the file.
3.  Make the file executable by running:
    ```bash
    chmod +x YaOG
    ```
4.  Run the application:
    ```bash
    ./YaOG
    ```
5.  On first launch, the application will create a `.env` file and a `models.json` in the same directory.
6.  Go to **Settings**, enter your OpenRouter API Key, and save.

### Running from Source
1.  Clone the repository.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the application:
    ```bash
    python yaog.py
    ```

## Technical Details
*   **Backend:** Python 3 (PyQt6)
*   **Frontend:** QWebEngineView (HTML/CSS/JavaScript)
*   **Database:** SQLite
*   **Communication:** QWebChannel (bridging Python signals and JavaScript)

## License
This project is licensed under the MIT License. See the LICENSE file for details.
