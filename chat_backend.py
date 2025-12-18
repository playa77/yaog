# chat_backend.py for YaOG
# Version: 3.7.0 (Phase 4: Pruning Update)
# Description: Bridges Python signals to JavaScript via QWebChannel.

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class ChatBackend(QObject):
    """
    The bridge object exposed to JavaScript.
    """
    # Signal to add a full message (used for history loading)
    message_added = pyqtSignal(int, str, str, str, name='message_added')
    # Signal to stream a single token
    token_received = pyqtSignal(str, name='token_received')
    
    # Signals from JS to Python
    edit_requested = pyqtSignal(int, str, name='edit_requested')
    regenerate_requested = pyqtSignal(int, name='regenerate_requested')
    delete_requested = pyqtSignal(int, name='delete_requested')

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    @pyqtSlot(int)
    def copy_message(self, index):
        """Called from JS when user clicks Copy."""
        self.main_window.copy_message_to_clipboard(index)
    
    @pyqtSlot(str)
    def stream_token(self, token):
        """Relays a token from the Python Worker -> Main Thread -> JS."""
        self.token_received.emit(token)

    @pyqtSlot(int, str)
    def request_edit(self, index, new_content):
        """Called from JS when user saves an edit."""
        self.edit_requested.emit(index, new_content)

    @pyqtSlot(int)
    def request_regenerate(self, index):
        """Called from JS when user clicks Regenerate."""
        self.regenerate_requested.emit(index)

    @pyqtSlot(int)
    def request_delete(self, index):
        """Called from JS when user clicks Delete."""
        self.delete_requested.emit(index)
