class Error(Exception):
    def __init__(self, message='', stderr=None):
        super().__init__(message)
        self.stderr = stderr
