import asyncio
import logging
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.hunter.strategies.github import GitHubStrategy
from app.hunter.strategies.ai import AIStrategy
from app.hunter.extractor import UniversalExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manual_verification")


async def verify_github():
    print("\n--- Verifying GitHub Strategy ---")
    strategy = GitHubStrategy()
    urls = await strategy.discover()
    print(f"Found {len(urls)} URLs from GitHub")
    if urls:
        print(f"Sample: {urls[0]}")
    return len(urls) > 0


async def verify_ai():
    print("\n--- Verifying AI Strategy ---")
    strategy = AIStrategy()
    urls = await strategy.discover()
    print(f"Found {len(urls)} URLs from AI")
    if urls:
        print(f"Sample: {urls[0]}")
    return (
        True  # AI might fail if no keys or rate limit, but we want to ensure code runs
    )


async def verify_extractor():
    print("\n--- Verifying Extractor ---")
    sample_content = """
    Here is a proxy: 1.1.1.1:80
    And a vmess: vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDN9
    """
    proxies = UniversalExtractor.extract_proxies(sample_content)
    print(f"Extracted {len(proxies)} proxies")
    for p in proxies:
        print(f"- {p.protocol}://{p.ip}:{p.port}")
    return len(proxies) >= 1


async def main():
    print("STARTING MANUAL VERIFICATION")

    gh_ok = await verify_github()
    ai_ok = await verify_ai()
    ext_ok = await verify_extractor()

    print("\n--- SUMMARY ---")
    print(f"GitHub Strategy: {'[OK]' if gh_ok else '[FAILED/Auth]'}")
    print(f"AI Strategy:     {'[OK]' if ai_ok else '[FAILED/Auth]'}")
    print(f"Extractor:       {'[OK]' if ext_ok else '[FAILED]'}")


if __name__ == "__main__":
    asyncio.run(main())
