from loguru import logger


async def trigger_match(biz_type: str, item_id: str) -> None:
    """
    Stub for match triggering. Will be implemented in the match module (Backend B).

    See docs/architecture/matching-rules.md for scoring weights and thresholds.
    """
    logger.info(f"[match-stub] trigger_match called: biz_type={biz_type}, item_id={item_id}")
