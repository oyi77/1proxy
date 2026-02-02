import re
import logging
from typing import List
from app.hunter.strategy import BaseStrategy

# Try to import g4f, but handle failure if not installed (though we just installed it)
try:
    from g4f.client import AsyncClient
    from g4f.Provider import RetryProvider, PollinationsAI, BlackboxPro

    HAS_G4F = True
except ImportError:
    HAS_G4F = False
    AsyncClient = None  # Ensure attribute exists for patching in tests
    RetryProvider = None
    PollinationsAI = None
    BlackboxPro = None

logger = logging.getLogger(__name__)


class AIStrategy(BaseStrategy):
    PROMPT = (
        "Find me 5 working URLS for free proxy lists updated in the last 24 hours. "
        "They should be direct links to raw text files on GitHub, Pastebin, or similar sites. "
        "Do not explain. Just list the URLs starting with https://."
    )

    @property
    def name(self) -> str:
        return "ai"

    async def discover(self) -> List[str]:
        if not HAS_G4F:
            logger.warning("g4f library not installed, skipping AI strategy")
            return []

        try:
            # Simple list of providers that don't usually fail with auth errors
            providers = [PollinationsAI, BlackboxPro]

            client = AsyncClient(provider=RetryProvider(providers))

            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": self.PROMPT}],
            )

            content = response.choices[0].message.content
            if not content:
                return []

            return self._extract_urls(content)

        except Exception as e:
            logger.error(f"AI Strategy failed: {str(e)}")
            return []

    def _extract_urls(self, text: str) -> List[str]:
        # Regex to find https:// URLs
        url_pattern = re.compile(r'https://[^\s<>"]+|www\.[^\s<>"]+')
        return [url for url in url_pattern.findall(text) if "http" in url]
