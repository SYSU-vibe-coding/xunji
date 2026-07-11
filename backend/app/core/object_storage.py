from __future__ import annotations

import io
import re
import uuid
import warnings
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import unquote, urlparse

from minio import Minio
from minio.error import S3Error
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.common.errors import BizError, ErrorCode
from app.common.utils import now_beijing
from app.core.config import Settings, settings

ASSET_PREFIX = "asset://"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
UPLOAD_BIZ_TYPES = {"LOST", "FOUND", "CLAIM_PROOF", "CERT", "USER"}
_KEY_PATTERN = re.compile(
    r"^(?P<biz>[A-Z_]+)/(?P<user>[A-Za-z0-9_-]+)/(?P<month>\d{6})/"
    r"(?P<name>[0-9a-f]{32})\.(?P<ext>jpg|png|webp)$"
)
_FORMAT_CONFIG: dict[str, tuple[str, str]] = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}


@dataclass(frozen=True)
class SanitizedImage:
    data: bytes
    extension: str
    content_type: str


@dataclass(frozen=True)
class StoredAsset:
    asset_ref: str
    preview_url: str
    content_type: str
    size: int


class ObjectStorage:
    def __init__(self, config: Settings = settings) -> None:
        self._settings = config
        self._client = Minio(
            config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=config.MINIO_SECURE,
        )
        public_url = urlparse(config.minio_public_base_url)
        if public_url.scheme not in {"http", "https"} or not public_url.netloc:
            raise RuntimeError("MINIO_PUBLIC_BASE_URL must be an absolute HTTP(S) URL")
        if public_url.path not in {"", "/"}:
            raise RuntimeError("MINIO_PUBLIC_BASE_URL must not contain a path")
        self._signing_client = Minio(
            public_url.netloc,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=public_url.scheme == "https",
        )

    async def ensure_private_bucket(self) -> None:
        await run_in_threadpool(self._ensure_private_bucket_sync)

    def _ensure_private_bucket_sync(self) -> None:
        bucket = self._settings.MINIO_BUCKET
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)
        try:
            self._client.delete_bucket_policy(bucket)
        except S3Error as exc:
            if exc.code not in {"NoSuchBucketPolicy", "NoSuchPolicy"}:
                raise

    async def upload_image(self, raw: bytes, *, biz_type: str, user_id: str) -> StoredAsset:
        if biz_type not in UPLOAD_BIZ_TYPES:
            raise BizError(
                ErrorCode.PARAM_ERROR,
                f"bizType must be one of {sorted(UPLOAD_BIZ_TYPES)}",
            )
        image = sanitize_image(raw, max_pixels=self._settings.MINIO_MAX_IMAGE_PIXELS)
        month = now_beijing().strftime("%Y%m")
        object_key = f"{biz_type}/{user_id}/{month}/{uuid.uuid4().hex}.{image.extension}"

        def put() -> None:
            self._ensure_private_bucket_sync()
            self._client.put_object(
                self._settings.MINIO_BUCKET,
                object_key,
                io.BytesIO(image.data),
                length=len(image.data),
                content_type=image.content_type,
                metadata={"biz-type": biz_type, "uploader-id": user_id},
            )

        try:
            await run_in_threadpool(put)
            preview_url = await self._presign_key(object_key, sensitive=True)
        except BizError:
            raise
        except Exception as exc:
            raise BizError(ErrorCode.STORAGE_ERROR) from exc
        return StoredAsset(
            asset_ref=f"{ASSET_PREFIX}{object_key}",
            preview_url=preview_url,
            content_type=image.content_type,
            size=len(image.data),
        )

    async def validate_owned_asset(
        self, asset_ref: str, *, user_id: str, biz_type: str
    ) -> str:
        object_key = self._new_asset_key(asset_ref)
        match = _KEY_PATTERN.fullmatch(object_key)
        if match is None or match.group("biz") != biz_type:
            raise BizError(ErrorCode.PARAM_ERROR, f"图片引用必须属于 {biz_type} 业务")
        if match.group("user") != user_id:
            raise BizError(ErrorCode.FORBIDDEN, "不可使用其他用户上传的图片")
        try:
            await run_in_threadpool(
                self._client.stat_object,
                self._settings.MINIO_BUCKET,
                object_key,
            )
        except Exception as exc:
            raise BizError(ErrorCode.PARAM_ERROR, "图片引用不存在或不可用") from exc
        return asset_ref

    async def validate_owned_assets(
        self, asset_refs: list[str], *, user_id: str, biz_type: str
    ) -> list[str]:
        for asset_ref in asset_refs:
            await self.validate_owned_asset(asset_ref, user_id=user_id, biz_type=biz_type)
        return asset_refs

    async def sign_reference(self, stored_ref: str | None, *, sensitive: bool) -> str | None:
        if not stored_ref:
            return None
        object_key = self.object_key_from_stored_reference(stored_ref)
        if object_key is None:
            return None
        try:
            return await self._presign_key(object_key, sensitive=sensitive)
        except Exception as exc:
            raise BizError(ErrorCode.STORAGE_ERROR) from exc

    def stable_asset_ref(self, stored_ref: str | None) -> str | None:
        if not stored_ref:
            return None
        object_key = self.object_key_from_stored_reference(stored_ref)
        return f"{ASSET_PREFIX}{object_key}" if object_key is not None else None

    def editable_asset_ref(
        self, stored_ref: str | None, *, user_id: str, biz_type: str
    ) -> str | None:
        stable_ref = self.stable_asset_ref(stored_ref)
        if stable_ref is None:
            return None
        match = _KEY_PATTERN.fullmatch(stable_ref[len(ASSET_PREFIX) :])
        if (
            match is None
            or match.group("user") != user_id
            or match.group("biz") != biz_type
        ):
            return None
        return stable_ref

    async def sign_references(self, stored_refs: list[str], *, sensitive: bool) -> list[str]:
        signed: list[str] = []
        for stored_ref in stored_refs:
            url = await self.sign_reference(stored_ref, sensitive=sensitive)
            if url is not None:
                signed.append(url)
        return signed

    async def sign_reference_for_ai(self, stored_ref: str | None) -> str | None:
        """Sign a private object for container-internal AI access only."""
        if not stored_ref:
            return None
        object_key = self.object_key_from_stored_reference(stored_ref)
        if object_key is None:
            return None
        try:
            return await run_in_threadpool(
                self._client.presigned_get_object,
                self._settings.MINIO_BUCKET,
                object_key,
                expires=timedelta(minutes=self._settings.MINIO_AI_URL_EXPIRE_MINUTES),
            )
        except Exception as exc:
            raise BizError(ErrorCode.STORAGE_ERROR) from exc

    async def sign_references_for_ai(self, stored_refs: list[str]) -> list[str]:
        signed: list[str] = []
        for stored_ref in stored_refs:
            url = await self.sign_reference_for_ai(stored_ref)
            if url is not None:
                signed.append(url)
        return signed

    async def _presign_key(self, object_key: str, *, sensitive: bool) -> str:
        hours = (
            self._settings.MINIO_SENSITIVE_EXPIRE_HOURS
            if sensitive
            else self._settings.MINIO_URL_EXPIRE_HOURS
        )
        return await run_in_threadpool(
            self._signing_client.presigned_get_object,
            self._settings.MINIO_BUCKET,
            object_key,
            expires=timedelta(hours=hours),
        )

    def object_key_from_stored_reference(self, stored_ref: str) -> str | None:
        if stored_ref.startswith(ASSET_PREFIX):
            key = stored_ref[len(ASSET_PREFIX) :]
            return key if self._is_safe_key(key) else None

        parsed = urlparse(stored_ref)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        allowed_hosts = {
            urlparse(self._settings.minio_public_base_url).netloc,
            self._settings.MINIO_ENDPOINT,
        }
        if parsed.netloc not in allowed_hosts:
            return None
        prefix = f"/{self._settings.MINIO_BUCKET}/"
        if not parsed.path.startswith(prefix):
            return None
        key = unquote(parsed.path[len(prefix) :])
        return key if self._is_safe_key(key) else None

    @staticmethod
    def _new_asset_key(asset_ref: str) -> str:
        if not asset_ref.startswith(ASSET_PREFIX):
            raise BizError(ErrorCode.PARAM_ERROR, "图片字段只接受上传接口返回的 assetRef")
        key = asset_ref[len(ASSET_PREFIX) :]
        if not ObjectStorage._is_safe_key(key):
            raise BizError(ErrorCode.PARAM_ERROR, "assetRef 格式无效")
        return key

    @staticmethod
    def _is_safe_key(key: str) -> bool:
        return bool(key) and not key.startswith("/") and ".." not in key.split("/")


def sanitize_image(raw: bytes, *, max_pixels: int) -> SanitizedImage:
    if not raw:
        raise BizError(ErrorCode.UPLOAD_FAILED, "图片内容为空")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise BizError(ErrorCode.UPLOAD_FAILED, "文件大小不能超过 10MB")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                image_format = source.format
                if image_format not in _FORMAT_CONFIG:
                    raise BizError(ErrorCode.PARAM_ERROR, "仅支持 JPEG/PNG/WebP 格式")
                if source.width * source.height > max_pixels:
                    raise BizError(ErrorCode.UPLOAD_FAILED, "图片像素尺寸过大")
                source.load()
                if image_format == "JPEG":
                    clean = source.convert("RGB")
                elif "A" in source.getbands() or "transparency" in source.info:
                    clean = source.convert("RGBA")
                else:
                    clean = source.convert("RGB")
    except BizError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise BizError(ErrorCode.UPLOAD_FAILED, "图片像素尺寸过大") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise BizError(ErrorCode.PARAM_ERROR, "文件内容不是有效图片") from exc

    extension, content_type = _FORMAT_CONFIG[image_format]
    output = io.BytesIO()
    save_options: dict[str, int | bool] = {}
    if image_format == "JPEG":
        save_options = {"quality": 90, "optimize": True}
    elif image_format == "WEBP":
        save_options = {"quality": 90, "method": 4}
    clean.save(output, format=image_format, **save_options)
    return SanitizedImage(
        data=output.getvalue(),
        extension=extension,
        content_type=content_type,
    )


_object_storage = ObjectStorage()


def get_object_storage() -> ObjectStorage:
    return _object_storage
