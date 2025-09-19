"""Project source package.

Exposes key entrypoints for external use/tests.
"""

from .inference import run as run_inference  # re-export for convenience

__all__ = [
    'run_inference',
]
