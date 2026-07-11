from datetime import datetime

import pytest
from app.claim.models import ClaimRequest
from app.claim.service import ClaimService
from app.common.errors import BizError, ErrorCode
from app.db.ulid import generate_ulid
from app.item.models import FoundItem, ItemImage
from app.user.models import UserCertRequest
from app.user.schemas import CurrentUser
from app.user.service import UserService

CLAIMANT = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")
FINDER = CurrentUser(id="01TESTSTAFF00000000000001", role="STAFF", status="ACTIVE")
OUTSIDER = CurrentUser(id="01OUTSIDER000000000000001", role="USER", status="ACTIVE")
ADMIN = CurrentUser(id="01TESTADMIN00000000000001", role="ADMIN", status="ACTIVE")


async def test_certification_is_signed_for_applicant_and_admin_only(
    session, seeded_users
) -> None:
    cert_ref = f"asset://CERT/{CLAIMANT.id}/202607/{'c' * 32}.jpg"
    cert = UserCertRequest(
        id=generate_ulid(),
        user_id=CLAIMANT.id,
        campus_id="20260001",
        document_image_url=cert_ref,
        review_status="PENDING",
    )
    session.add(cert)
    await session.commit()

    applicant_view = await UserService(session).get_certification(CLAIMANT)
    assert applicant_view is not None
    assert applicant_view.document_image_ref == cert_ref
    assert applicant_view.document_image_url.startswith("https://signed.test/")

    from app.admin.service import AdminService

    admin_view = await AdminService(session).list_certifications("PENDING", 1, 10)
    assert admin_view["list"][0]["documentImageUrl"].startswith("https://signed.test/")


async def test_claim_proof_is_signed_only_after_party_or_admin_authorization(
    session, seeded_users, mock_minio
) -> None:
    found_id = generate_ulid()
    claim_id = generate_ulid()
    proof_ref = f"asset://CLAIM_PROOF/{CLAIMANT.id}/202607/{'d' * 32}.png"
    session.add_all(
        [
            FoundItem(
                id=found_id,
                user_id=FINDER.id,
                item_name="Wallet",
                category="DAILY_USE",
                found_time=datetime(2026, 7, 1, 10, 0),
                found_location="Library",
                custody_type="SELF",
                contact_preference="IN_APP",
                status="CLAIMING",
                review_status="APPROVED",
            ),
            ClaimRequest(
                id=claim_id,
                found_item_id=found_id,
                claimant_id=CLAIMANT.id,
                verify_level="LEVEL_2",
                review_status="ANSWER_PASSED",
            ),
            ItemImage(
                id=generate_ulid(),
                biz_type="CLAIM_PROOF",
                biz_id=claim_id,
                image_url=proof_ref,
                sort_order=0,
            ),
        ]
    )
    await session.commit()

    claimant_view = await ClaimService(session).get_claim_detail(claim_id, CLAIMANT)
    assert claimant_view.proof_image_urls[0].startswith("https://signed.test/")
    finder_view = await ClaimService(session).get_claim_detail(claim_id, FINDER)
    assert finder_view.proof_image_urls[0].startswith("https://signed.test/")

    mock_minio.signer.reset_mock()
    with pytest.raises(BizError) as outsider:
        await ClaimService(session).get_claim_detail(claim_id, OUTSIDER)
    assert outsider.value.code == ErrorCode.CLAIM_NOT_PARTY
    mock_minio.signer.presigned_get_object.assert_not_called()

    admin_view = await ClaimService(session).get_claim_detail(claim_id, ADMIN)
    assert admin_view.proof_image_urls[0].startswith("https://signed.test/")
