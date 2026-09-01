"""
Shared exception types for Sub-auto.
"""


class TranslationCancelled(Exception):
    """
    Raised internally when the user cancels (or stops) a translation job.

    Used instead of ``KeyboardInterrupt`` for control flow so that worker
    threads can exit cleanly: it is an ordinary ``Exception`` and is handled
    by the orchestrator's exception handlers without leaving an unhandled
    traceback behind.
    """
    pass
