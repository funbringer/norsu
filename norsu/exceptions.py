class ProcessError(Exception):
    """
    This exception represents a failed invocation of an external tool.
    """
    def __init__(self, message='', stderr=None):
        super().__init__(message)
        self.stderr = stderr


class LogicError(Exception):
    """
    Main application error.
    """
