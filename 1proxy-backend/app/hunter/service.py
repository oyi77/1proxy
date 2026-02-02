import logging
import aiohttp
import asyncio
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.db_models import CandidateSource, ProxySource
from app.hunter.strategies.github import GitHubStrategy
from app.hunter.strategies.ai import AIStrategy
from app.hunter.strategies.search import SearchStrategy
from app.hunter.strategies.telegram import TelegramStrategy
from app.hunter.extractor import UniversalExtractor

logger = logging.getLogger(__name__)


class HunterService:
    def __init__(self):
        self.strategies = [
            GitHubStrategy(),
            AIStrategy(),
            SearchStrategy(),
            TelegramStrategy(),
        ]

    async def run_hunt(self):
        """
        Execute all discovery strategies and process results.
        """
        logger.info("Starting Hunter Protocol...")

        discovered_urls = set()

        # 1. Run all strategies concurrently
        tasks = [strategy.discover() for strategy in self.strategies]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            strategy_name = self.strategies[i].name
            if isinstance(result, Exception):
                logger.error(f"Strategy {strategy_name} failed: {result}")
                continue

            if result:
                logger.info(f"Strategy {strategy_name} found {len(result)} URLs")
                for url in result:
                    discovered_urls.add((url, strategy_name))

        # 2. Process unique URLs
        logger.info(f"Total unique candidates found: {len(discovered_urls)}")

        async for session in get_db():
            for url, method in discovered_urls:
                await self.process_candidate(session, url, method)
            await session.commit()

        logger.info("Hunter Protocol complete.")

    async def process_candidate(self, session: AsyncSession, url: str, method: str):
        """
        Check if URL is new, save it, and score it.
        """
        # Check if already exists in Candidates
        stmt = select(CandidateSource).where(CandidateSource.url == url)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            logger.debug(f"Candidate already exists: {url}")
            return

        # Check if already exists in Active Sources
        stmt = select(ProxySource).where(ProxySource.url == url)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            logger.debug(f"Source already active: {url}")
            return

        # Fetch and Analyze
        try:
            content = await self._fetch_content(url)
            proxies = UniversalExtractor.extract_proxies(content, source_url=url)

            confidence = self._calculate_confidence(url, proxies)

            # Save
            candidate = CandidateSource(
                url=url,
                domain=self._extract_domain(url),
                discovery_method=method,
                status="pending",
                confidence_score=confidence,
                proxies_found_count=len(proxies),
                last_checked_at=datetime.utcnow(),
            )
            session.add(candidate)
            logger.info(
                f"Added candidate: {url} (Score: {confidence}, Proxies: {len(proxies)})"
            )

        except Exception as e:
            logger.warning(f"Failed to process candidate {url}: {str(e)}")
            # We might still save it as 'failed' or 'pending' retry?
            # For now, skip invalid URLs to keep DB clean.

    async def _fetch_content(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                return await resp.text()

    def _calculate_confidence(self, url: str, proxies: List[any]) -> int:
        score = 0

        # Domain Trust
        if "github.com" in url or "raw.githubusercontent.com" in url:
            score += 20
        elif "pastebin.com" in url:
            score += 10

        # Content Volume
        count = len(proxies)
        if count > 0:
            score += 10
        if count > 50:
            score += 20
        if count > 500:
            score += 20

        # Protocol Diversity
        protocols = {p.protocol for p in proxies}
        if len(protocols) > 1:
            score += 10
        if "vmess" in protocols or "vless" in protocols:
            score += 10

        return min(score, 100)

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse

        try:
            return urlparse(url).netloc
        except:
            return ""
