class UnknownMessageTypeError(Exception):
    def __init__(self, message_type: str):
        super().__init__(f"Unknown message type: {message_type!r}")
        self.message_type = message_type