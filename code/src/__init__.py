"""src package exports used by notebooks.

This package exposes the two modules included in this folder so notebooks
can do `from src import ml_kem` or `from src import hill_cypher` and also
support `from src import *` if desired.
"""

# Use package-relative imports so the package works when imported as `src`.
from . import ml_kem
from . import hill_cypher

# Explicit export list (makes `from src import *` cleaner)
__all__ = ["ml_kem", "hill_cypher"]
