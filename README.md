# YaOG
**Yet Another OpenRouter GUI**

> **Version:** 2.4.3
> **Status:** Milestone 2 Complete (Advanced Features & UX Polish)

YaOG is a robust, standalone desktop application built with Python and PyQt6. It serves as a feature-rich, local-first graphical user interface for interacting with the OpenRouter.ai API. It prioritizes user privacy by storing all conversation history locally via SQLite and offers power-user features like file attachments, system prompt management, and granular model control.

This application is designed and tested specifically for Linux environments.

---

## Key Features

### Core Chat Experience
*   **Multi-Model Support:** Seamlessly switch between models (e.g., Mistral, Llama 3, Gemma) per message generation.
*   **Parameter Control:** Adjust temperature via a slider to control creativity.
*   **Streamed Responses:** Real-time text streaming for a responsive feel.
*   **Token Counting:** Real-time context token estimation using `tiktoken`.

### Advanced Capabilities (Milestone 2)
*   **File Attachments:**
    *   Upload text-based files (Code, Logs, CSV, JSON, Markdown) and PDFs.
    *   Automatic text extraction (using `PyMuPDF` for PDFs) injected directly into the context.
    *   Staging area to review attachments before sending.
*   **System Prompt Manager:**
    *   Create, Edit, Save, and Delete custom system personas (e.g., "Coding Assistant", "Creative Writer").
    *   Select a saved prompt from a dropdown to instantly apply it to the current chat.
*   **Markdown Rendering:**
    *   Toggleable "Render Markdown" checkbox.
    *   View code blocks, tables, and formatting, or switch to raw text for copying.
*   **Local Persistence:**
    *   All chats and messages are saved automatically to a local SQLite database (`~/.or-client/or-client.db`).
    *   History persists across sessions.

### UX Enhancements
*   **Chat Management:** Right-click conversations in the history sidebar to **Rename** or **Delete** them.
*   **Copy Tools:** One-click "Copy" button for every assistant message (strips out hidden attachment metadata automatically).
*   **Copy Full Conversation:** Button to copy the entire chat log to the clipboard.
*   **Locked UI:** Clean, fixed-layout dock widgets for a stable desktop experience.

---

## Installation

### Prerequisites
*   **Python 3.10+**
*   An API Key from OpenRouter.ai

### Setup

1.  **Clone or Download the Repository:**

        git clone <repository-url>
        cd yaog

2.  **Create a Virtual Environment (Recommended):**

        python -m venv venv
        source venv/bin/activate

3.  **Install Dependencies:**

        pip install -r requirements.txt

4.  **Configuration:**
    *   The application will automatically generate a `.env` file and a `models.json` file on the first run if they are missing.
    *   Open `.env` and paste your API key:

            OPENROUTER_API_KEY="sk-or-v1-..."

    *   (Optional) Edit `models.json` to add your preferred OpenRouter model IDs.

---

## Usage

### Running the App

    python yaog.py

### Workflow
1.  **Select a Model:** Choose a model from the dropdown in the top-right.
2.  **Set System Prompt (Optional):** Select a pre-saved prompt or click "Manage Prompts" to create a new one.
3.  **Attach Files:** Click the "Attach" button to select files. They will appear in the staging area above the input box.
4.  **Chat:** Type your message and hit "Send".
5.  **Manage History:**
    *   Click a chat in the left sidebar to load it.
    *   **Right-click** a chat title to Rename or Delete it.

---

## Architecture

The application follows a modular design separating UI, Logic, and Data:

*   **`yaog.py`**: Main entry point. Handles the `QMainWindow`, UI layout, and connects signals/slots.
*   **`api_manager.py`**: Handles HTTP requests to OpenRouter using `httpx` (supports SSE streaming).
*   **`database_manager.py`**: Manages the SQLite database (Schema migration, CRUD for Chats/Messages/Prompts).
*   **`worker_manager.py`**: Runs API calls in background threads (`QThreadPool`) to keep the UI responsive.
*   **`chat_template.html`**: The frontend view layer running inside `QWebEngineView`.
*   **`utils.py`**: Utilities for file extraction (`FileExtractor`), token counting (`TokenCounter`), and crash handling.

---

## Roadmap

### Completed
*   [x] Core MVP (Chat, History, Settings).
*   [x] Database Persistence.
*   [x] System Prompt Management (CRUD).
*   [x] File Attachments (PDF & Text).
*   [x] Markdown Rendering.
*   [x] Context Menu (Rename/Delete).
*   [x] Token Counter.

### Upcoming / Postponed
*   [ ] **History Organization:** Search functionality and Tagging system for conversations (Postponed to future milestone).
*   [ ] **UI Theming:** Night/Day mode toggles and font size adjustments.
*   [ ] **Batch Uploads:** Enhanced UI for selecting multiple documents simultaneously.
*   [ ] **Packaging:** Build scripts (PyInstaller) for standalone executables.

---

## License
This project is open-source. Feel free to modify and distribute.
