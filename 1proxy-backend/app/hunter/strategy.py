from abc import ABC, abstractmethod
from typing import List


class BaseStrategy(ABC):
    """
    Abstract base class for proxy discovery strategies.
    Each strategy implements a method to find potential proxy source URLs.
    """

    @abstractmethod
    async def discover(self) -> List[str]:
        """
        Run the discovery process.
        Returns a list of raw URLs that might contain proxies.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the strategy (e.g., 'github', 'ai')"""
        pass
