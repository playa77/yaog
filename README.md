# YaOG - Yet another Openrouter GUI

YaOG is a standalone, lightweight Linux desktop client for the OpenRouter.ai API, built using Python and PyQt6. It provides a persistent, customizable chat interface with support for multiple models, file attachments, system prompts, and local data management.

## Features

**Core Chat Functionality**
*   **Multi-Model Support:** Seamlessly switch between different LLMs (e.g., Mistral, Gemini, DeepSeek) within the same application.
*   **Markdown Rendering:** Chat output supports full Markdown rendering, including syntax highlighting for code blocks and tables.
*   **Streaming Responses:** Real-time text generation feedback.
*   **Token Counting:** Real-time estimation of context token usage using tiktoken.

**Data & Persistence**
*   **Local Database:** All conversations and messages are automatically saved to a local SQLite database (~/.or-client/or-client.db).
*   **History Management:** Rename and delete saved conversations via the sidebar.
*   **Import/Export:** Export specific conversations or system prompts to JSON for backup or sharing. Import them back into the application via the context menu.

**Context & Attachments**
*   **File Attachments:** Attach text-based files (Code, Logs, Markdown, CSV) and PDF documents to the chat context. The application automatically extracts text from these files.
*   **System Prompts:** Create, save, and manage custom system instructions (personas) to guide the AI's behavior.

**Configuration**
*   **GUI Settings:** Manage API keys, timeouts, and font sizes directly through the application interface.
*   **Model Manager:** Add, edit, or remove available models via the Settings dialog without editing configuration files manually.

## Prerequisites

*   **Linux OS**
*   **Python 3.10+**
*   **OpenRouter API Key:** You need a valid API key from openrouter.ai.

## Installation

1.  **Clone or Download the Repository**
    Ensure all source files (yaog.py, api_manager.py, database_manager.py, settings_manager.py, worker_manager.py, utils.py, chat_template.html) are in the same directory.

2.  **Create a Virtual Environment (Recommended)**

    python -m venv venv
    source venv/bin/activate

3.  **Install Dependencies**
    Use the provided requirements.txt file:

    pip install -r requirements.txt

    Dependencies include: PyQt6, PyQt6-WebEngine, httpx, python-dotenv, pymupdf, markdown, tiktoken.

## Configuration

Upon the first launch, YaOG will automatically generate the necessary configuration files if they are missing:

*   .env: Stores your API Key.
*   models.json: Stores the list of available models.
*   settings.json: Stores UI preferences (font size, timeout).

### Setting the API Key
1.  Launch the application.
2.  Click the **Settings** button in the bottom right.
3.  Navigate to the **API & Network** tab.
4.  Enter your OpenRouter API Key and click **Update API Key**.

## Usage

### Running the Application

    python yaog.py

### Managing Chats
*   **New Chat:** Click the "New Chat" button in the top left.
*   **Load Chat:** Click any item in the "Saved Conversations" list.
*   **Context Menu:** Right-click on a chat in the list to **Rename**, **Delete**, or **Export** it.
*   **Import Chat:** Right-click anywhere in the "Saved Conversations" list area and select **Import Chat (JSON)**.

### Managing Models
1.  Go to **Settings > Models**.
2.  Use the **Add**, **Edit**, or **Delete** buttons to configure which models appear in the main dropdown.
3.  You will need the specific Model ID string from OpenRouter (e.g., mistralai/mistral-7b-instruct:free).

### File Attachments
Click the **Attach** button next to the input box to select files. Supported formats include PDF, TXT, MD, PY, JS, HTML, JSON, CSV, and logs. The content of the files is extracted and appended to your message.

## Troubleshooting

**WebEngine Issues**
If the application crashes or displays a blank white screen, it may be due to GPU acceleration issues with QtWebEngine on certain Linux configurations. The application attempts to handle this automatically by passing --no-sandbox and --disable-gpu arguments on startup.

**Missing Files**
If chat_template.html is missing, the chat view will not load. Ensure this file exists in the root directory.

## License

This project is provided as-is for educational and personal use.
