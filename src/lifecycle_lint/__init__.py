"""lifecycle-lint: auditoria estática de jornadas de CRM."""

from .loader import JourneyParseError, load_journey, load_journeys
from .model import Finding, Journey
from .rules import DEFAULT_CONFIG, REGISTRY, run_all

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_CONFIG",
    "REGISTRY",
    "Finding",
    "Journey",
    "JourneyParseError",
    "load_journey",
    "load_journeys",
    "run_all",
]
