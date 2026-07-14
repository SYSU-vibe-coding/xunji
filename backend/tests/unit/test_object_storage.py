import io
from datetime import timedelta

import pytest
from app.common.errors import BizError, ErrorCode
from app.core.config import settings
from app.core.object_storage import MAX_UPLOAD_BYTES, get_object_storage, sanitize_image
from app.item.service import ItemService
from app.user.schemas import CurrentUser
from fastapi import UploadFile
from PIL import Image, PngImagePlugin
from starlette.datastructures import Headers


def _png_bytes(*, metadata: bool = False) -> bytes:
    output = io.BytesIO()
    pnginfo = None
    if metadata:
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("private", "must-be-removed")
    Image.new("RGB", (12, 8), color=(20, 40, 60)).save(output, format="PNG", pnginfo=pnginfo)
    return output.getvalue()


async def test_bucket_is_private_and_existing_policy_is_deleted(mock_minio) -> None:
    await mock_minio.storage.ensure_private_bucket()

    mock_minio.client.delete_bucket_policy.assert_called_once_with(settings.MINIO_BUCKET)
    mock_minio.client.set_bucket_policy.assert_not_called()


async def test_upload_uses_real_format_reencodes_and_strips_metadata(mock_minio) -> None:
    stored = await mock_minio.storage.upload_image(
        _png_bytes(metadata=True),
        biz_type="FOUND",
        user_id="01TESTUSER000000000000001",
    )

    assert stored.asset_ref.startswith("asset://FOUND/01TESTUSER000000000000001/")
    assert stored.asset_ref.endswith(".png")
    assert stored.content_type == "image/png"
    assert stored.preview_url.startswith("https://signed.test/")
    put_call = mock_minio.client.put_object.call_args
    assert put_call.kwargs["content_type"] == "image/png"
    uploaded = put_call.args[2].read()
    with Image.open(io.BytesIO(uploaded)) as clean:
        assert clean.format == "PNG"
        assert "private" not in clean.info


async def test_upload_ignores_spoofed_mime_and_filename(session, mock_minio) -> None:
    upload = UploadFile(
        io.BytesIO(_png_bytes()),
        filename="claimed-jpeg.jpg",
        headers=Headers({"content-type": "image/jpeg"}),
    )
    user = CurrentUser(id="01TESTUSER000000000000001", role="USER", status="ACTIVE")

    result = await ItemService(session).upload_file(upload, "LOST", user)

    assert result["assetRef"].endswith(".png")
    assert result["contentType"] == "image/png"

    fake_image = UploadFile(
        io.BytesIO(b"not an image"),
        filename="fake.png",
        headers=Headers({"content-type": "image/png"}),
    )
    with pytest.raises(BizError) as invalid:
        await ItemService(session).upload_file(fake_image, "LOST", user)
    assert invalid.value.code == ErrorCode.PARAM_ERROR


def test_invalid_image_payload_and_excessive_pixels_are_rejected() -> None:
    with pytest.raises(BizError) as invalid:
        sanitize_image(b"not a jpeg", max_pixels=1_000)
    assert invalid.value.code == ErrorCode.PARAM_ERROR

    with pytest.raises(BizError) as oversized:
        sanitize_image(_png_bytes(), max_pixels=95)
    assert oversized.value.code == ErrorCode.UPLOAD_FAILED

    with pytest.raises(BizError) as too_large:
        sanitize_image(b"x" * (MAX_UPLOAD_BYTES + 1), max_pixels=1_000)
    assert too_large.value.code == ErrorCode.UPLOAD_FAILED
    assert "20MB" in too_large.value.message


async def test_new_asset_references_enforce_owner_and_reject_external_urls(mock_minio) -> None:
    storage = get_object_storage()
    other_ref = f"asset://LOST/other-user/202607/{'a' * 32}.jpg"
    with pytest.raises(BizError) as wrong_owner:
        await storage.validate_owned_asset(
            other_ref,
            user_id="01TESTUSER000000000000001",
            biz_type="LOST",
        )
    assert wrong_owner.value.code == ErrorCode.FORBIDDEN

    with pytest.raises(BizError) as external:
        await storage.validate_owned_asset(
            "https://example.com/image.jpg",
            user_id="01TESTUSER000000000000001",
            biz_type="LOST",
        )
    assert external.value.code == ErrorCode.PARAM_ERROR
    mock_minio.client.stat_object.assert_not_called()

    own_ref = f"asset://LOST/01TESTUSER000000000000001/202607/{'f' * 32}.jpg"
    await storage.validate_owned_asset(
        own_ref,
        user_id="01TESTUSER000000000000001",
        biz_type="LOST",
    )
    mock_minio.client.stat_object.assert_called_once_with(
        settings.MINIO_BUCKET,
        own_ref.removeprefix("asset://"),
    )


async def test_legacy_project_minio_url_is_resigned_but_external_url_is_hidden(
    mock_minio,
) -> None:
    legacy = "http://127.0.0.1:9000/xunji/LOST/202604/legacy.jpg"
    signed = await mock_minio.storage.sign_reference(legacy, sensitive=False)

    assert signed == "https://signed.test/xunji/LOST/202604/legacy.jpg?signature=test"
    assert mock_minio.storage.stable_asset_ref(legacy) == "asset://LOST/202604/legacy.jpg"
    assert (
        mock_minio.storage.editable_asset_ref(
            legacy,
            user_id="01TESTUSER000000000000001",
            biz_type="LOST",
        )
        is None
    )
    assert (
        await mock_minio.storage.sign_reference("https://example.com/image.jpg", sensitive=False)
        is None
    )
    assert mock_minio.signer.presigned_get_object.call_args.kwargs["expires"] == timedelta(
        hours=settings.MINIO_URL_EXPIRE_HOURS
    )


async def test_sensitive_signatures_use_short_expiration(mock_minio) -> None:
    asset_ref = f"asset://CERT/01TESTUSER000000000000001/202607/{'b' * 32}.jpg"
    await mock_minio.storage.sign_reference(asset_ref, sensitive=True)

    assert mock_minio.signer.presigned_get_object.call_args.kwargs["expires"] == timedelta(
        hours=settings.MINIO_SENSITIVE_EXPIRE_HOURS
    )


async def test_ai_signatures_use_internal_endpoint_and_short_expiration(mock_minio) -> None:
    asset_ref = f"asset://FOUND/01TESTUSER000000000000001/202607/{'c' * 32}.jpg"

    signed = await mock_minio.storage.sign_reference_for_ai(asset_ref)

    assert signed is not None
    assert signed.startswith("http://minio:9000/")
    assert mock_minio.client.presigned_get_object.call_args.kwargs["expires"] == timedelta(
        minutes=settings.MINIO_AI_URL_EXPIRE_MINUTES
    )
    mock_minio.signer.presigned_get_object.assert_not_called()
