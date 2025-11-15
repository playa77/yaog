# OR-Client - A Standalone OpenRouter.ai Frontend

![Project Status: In Development](https://img.shields.io/badge/status-in%20development-orange)
![Language: Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Framework: PyQt6](https://img.shields.io/badge/Framework-PyQt6-green.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A fast, native, and uncluttered desktop application for Ubuntu Linux, designed to provide a power-user interface for the OpenRouter.ai API.

---

![OR-Client Screenshot](https://raw.githubusercontent.com/path/to/your/screenshot.png)
*(Note: Please replace the image link above with an actual screenshot of the application)*

### Core Philosophy

OR-Client is built for developers, writers, and AI power-users who want maximum, per-generation control over model parameters in a responsive, local-first environment. The user experience is inspired by the clean, three-panel layout of Google AI Studio, prioritizing workflow efficiency over non-essential features. All conversation data is stored locally in a SQLite database, ensuring user privacy and offline access to past chats.

### Features

-   **✅ Live OpenRouter Connection:** Connects securely to the OpenRouter API using your private API key.
-   **✅ Asynchronous API Calls:** The UI remains fast and responsive while waiting for model responses, thanks to a multi-threaded architecture.
-   **✅ Robust Streaming:** Handles streaming responses correctly, ensuring compatibility with even the slowest models without timeouts.
-   **✅ Granular Model Control:** Select from any model listed in your local `models.json` configuration.
-   **✅ Temperature Control:** Easily adjust the temperature for each generation.
-   **🚧 Full Conversation Persistence:** (In Progress) All conversations will be saved automatically to a local SQLite database.
-   **🚧 History Management:** (Planned) Load, search, and tag previous conversations.
-   **🚧 System Prompt Management:** (Planned) Create, save, and reuse custom system prompts and personas.

### Technology Stack

-   **Language:** Python 3.10+
-   **UI Framework:** PyQt6
-   **API Communication:** `httpx` for robust, asynchronous API calls.
-   **Configuration:** `python-dotenv` for API key management.
-   **Data Storage:** Python's built-in `sqlite3` module.
-   **Chat Rendering:** `QWebEngineView` for high-fidelity Markdown and code rendering.

### Getting Started

Follow these instructions to get a local copy up and running.

#### Prerequisites

-   Ubuntu Linux
-   Python 3.10 or newer
-   Git

#### Installation

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/your-username/or-client.git
    cd or-client
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required packages:**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Configure your API Key:**
    The script will automatically create a `.env` file on the first run if it doesn't exist. Open the `.env` file and replace `"YOUR_API_KEY_HERE"` with your actual OpenRouter API key.
    ```
    OPENROUTER_API_KEY="sk-or-v1-..."
    ```

5.  **Run the application:**
    ```sh
    python3 yaog.py
    ```

### Project Status

This project is actively under development and is currently focused on completing **Milestone 1: Build the Core MVP**. The immediate next steps involve implementing the database backend for conversation persistence and improving the chat rendering logic.

### Contributing

Contributions are welcome! If you have a suggestion or find a bug, please open an issue. If you'd like to contribute code, please fork the repository and submit a pull request.

### License

This project is licensed under the MIT License - see the `LICENSE` file for details.
