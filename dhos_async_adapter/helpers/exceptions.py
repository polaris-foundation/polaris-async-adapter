class RequeueMessageError(Exception):
    """
    An exception to be raised when we want a message to be requeued.
    Should be used when encountering transient errors that may resolve
    themselves, such as connectivity issues.
    """


class RejectMessageError(Exception):
    """
    An exception to be raised when we want a message to be rejected.
    Should be used when encountering fundamental errors that will not
    be resolved with further attempts, such as malformed messages.
    """
