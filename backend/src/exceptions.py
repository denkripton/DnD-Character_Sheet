class ServiceError(Exception):
    def __init__(self, msg: str, code: int):
        self.message = msg
        self.status_code = code
        super().__init__(self.message)
