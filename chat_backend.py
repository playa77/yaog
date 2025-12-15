# chat_backend.py for YaOG
# Version: 3.5.0
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

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    @pyqtSlot(int)
    def copy_message(self, index):
        """Called from JS when user clicks Copy."""
        self.main_window.copy_message_to_clipboard(index)
    
    @pyqtSlot(str)
    def stream_token(self, token):
        """
        Relays a token from the Python Worker -> Main Thread -> JS.
        """
        self.token_received.emit(token)
