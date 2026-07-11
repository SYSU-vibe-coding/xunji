from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_client import AIClient
from app.db.ulid import generate_ulid
from app.job.models import DurableJob
from app.job.repository import DurableJobRepository

JOB_TYPES = {"MATCH", "CLASSIFY", "SENSITIVE"}


async def enqueue_item_jobs(
    session: AsyncSession,
    *,
    biz_type: str,
    biz_id: str,
    has_images: bool,
) -> list[DurableJob]:
    """Write one item-change job set in the caller's database transaction."""
    job_types = ["MATCH", "CLASSIFY"]
    if biz_type == "FOUND" and has_images:
        job_types.append("SENSITIVE")
    return await enqueue_jobs(
        session,
        biz_type=biz_type,
        biz_id=biz_id,
        job_types=job_types,
    )


async def enqueue_jobs(
    session: AsyncSession,
    *,
    biz_type: str,
    biz_id: str,
    job_types: list[str],
) -> list[DurableJob]:
    if not job_types or not set(job_types) <= JOB_TYPES:
        raise ValueError("job_types contains an unsupported durable job type")
    repo = DurableJobRepository(session)
    version = await repo.next_biz_version(biz_type, biz_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    jobs = [
        DurableJob(
            id=generate_ulid(),
            job_type=job_type,
            biz_type=biz_type,
            biz_id=biz_id,
            biz_version=version,
            status="PENDING",
            attempts=0,
            run_after=now,
        )
        for job_type in job_types
    ]
    await repo.create_batch(jobs)
    return jobs


async def execute_durable_job(
    session: AsyncSession,
    job: DurableJob,
    *,
    ai_client: AIClient,
) -> None:
    """Execute a claimed job without committing the runner-owned transaction."""
    from app.item.service import ItemService, _classify_and_save, _detect_sensitive_and_save

    if job.biz_type not in {"LOST", "FOUND"}:
        raise ValueError(f"unsupported durable job biz type: {job.biz_type}")

    if await DurableJobRepository(session).has_newer_biz_version(job):
        return

    client = ai_client
    if job.job_type == "MATCH":
        from app.match.service import run_match_in_session

        await run_match_in_session(session, job.biz_type, job.biz_id, client)
        return

    item_service = ItemService(session)
    if job.biz_type == "LOST":
        await item_service.get_lost_item_for_update_internal(job.biz_id)
    else:
        await item_service.get_found_item_for_update_internal(job.biz_id)

    if job.job_type == "CLASSIFY":
        await _classify_and_save(session, job.biz_type, job.biz_id, client)
    elif job.job_type == "SENSITIVE":
        if job.biz_type != "FOUND":
            raise ValueError("SENSITIVE jobs only support FOUND items")
        await _detect_sensitive_and_save(session, job.biz_id, client)
    else:
        raise ValueError(f"unsupported durable job type: {job.job_type}")
