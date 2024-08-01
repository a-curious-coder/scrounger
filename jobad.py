from typing import List, Optional
from dataclasses import dataclass


@dataclass
class JobAd:
    """Data class to store job advertisement information."""
    url: str
    title: str
    description: str
    company: str
    location: Optional[str] = None
    salary: Optional[str] = None
