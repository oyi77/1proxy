import pytest


@pytest.mark.unit
def test_enhanced_scraping_service_constructs():
    # Ensure service can be constructed (regression for NameError/ImportError).
    from app.grabber.scraping_enhancements import (
        EnhancedScrapingService,
        ScrapingEnhancementConfig,
    )

    service = EnhancedScrapingService(config=ScrapingEnhancementConfig())
    assert service.proxy_rotator is not None
    assert service.request_queue is not None
    assert service.rate_limiter is not None
