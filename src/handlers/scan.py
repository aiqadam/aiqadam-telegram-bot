"""`/scan` handler (FR-BOT-003).

Operator-only FSM command. Prompts the operator to send a QR code image,
decodes it via pyzbar, and calls the operator check-in API endpoint.

QR decode uses pyzbar which wraps libzbar0. The decoded string is expected
to be a UUID (the registration's checkin_code) or a URL ending in one.
The API endpoint's extractUuidFromQr handles both formats.

If pyzbar is unavailable (e.g. libzbar0 not installed), the handler falls
back to asking the operator to enter the code manually.
"""

from __future__ import annotations

import io
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PhotoSize

from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import (
    ApiClient,
    ApiUnavailableError,
    CheckinIneligibleError,
    CheckinNotFoundError,
)
from src.states.scan import ScanStates

router = Router(name="scan")
logger = logging.getLogger(__name__)

_ACCESS_DENIED_KEY = "operator.access_denied"


def _decode_qr(image_bytes: bytes) -> str | None:
    """Decode the first QR code in an image using pyzbar.

    Returns the decoded string, or None if no QR code found or pyzbar
    is unavailable.
    """
    try:
        from PIL import Image  # type: ignore[import]
        from pyzbar.pyzbar import decode  # type: ignore[import]

        img = Image.open(io.BytesIO(image_bytes))
        results = decode(img)
        if results:
            return results[0].data.decode("utf-8", errors="replace")
        return None
    except ImportError:
        logger.warning("pyzbar or PIL not installed — QR decode unavailable")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("QR decode failed: %s", exc)
        return None


@router.message(Command("scan"))
async def handle_scan_command(
    message: Message,
    state: FSMContext,
    user_context: UserContext | None,
) -> None:
    lang = "ru"

    if user_context is None or not user_context.is_known or not user_context.is_operator():
        await message.answer(t(_ACCESS_DENIED_KEY, lang))
        return

    if user_context.country is None:
        await message.answer(t("events.unavailable", lang))
        return

    await state.update_data(country=user_context.country)
    await state.set_state(ScanStates.awaiting_qr_photo)
    await message.answer(t("scan.prompt", lang))


@router.message(ScanStates.awaiting_qr_photo)
async def handle_scan_photo(
    message: Message,
    state: FSMContext,
    api_client: ApiClient,
) -> None:
    lang = "ru"
    data = await state.get_data()
    country = data.get("country", "")
    await state.clear()

    # Support both photo messages and document (uncompressed) messages.
    photo: PhotoSize | None = None
    if message.photo:
        photo = message.photo[-1]  # largest resolution
    elif (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith("image/")
    ):
        # Treat image documents the same as photos.
        doc_file = await message.bot.get_file(message.document.file_id)  # type: ignore[union-attr]
        raw = await message.bot.download_file(doc_file.file_path or "")  # type: ignore[union-attr]
        image_bytes = raw.read() if raw else b""
        await _process_image_bytes(message, image_bytes, country, api_client, lang)
        return
    else:
        await message.answer(t("scan.no_photo", lang))
        return

    file = await message.bot.get_file(photo.file_id)  # type: ignore[union-attr]
    raw = await message.bot.download_file(file.file_path or "")  # type: ignore[union-attr]
    image_bytes = raw.read() if raw else b""
    await _process_image_bytes(message, image_bytes, country, api_client, lang)


async def _process_image_bytes(
    message: Message,
    image_bytes: bytes,
    country: str,
    api_client: ApiClient,
    lang: str,
) -> None:
    qr_data = _decode_qr(image_bytes)
    if not qr_data:
        await message.answer(t("scan.no_qr_found", lang))
        return

    try:
        result = await api_client.operator_checkin(qr_code_data=qr_data, country=country)
    except CheckinNotFoundError:
        await message.answer(t("scan.not_found", lang))
        return
    except CheckinIneligibleError:
        await message.answer(t("scan.ineligible", lang))
        return
    except ApiUnavailableError:
        await message.answer(t("event.unavailable", lang))
        return

    if result.already_checked_in:
        await message.answer(
            t("scan.already_checked_in", lang).format(
                member=result.member_name or t("scan.unknown_member", lang),
                event=result.event_title,
            )
        )
    else:
        await message.answer(
            t("scan.success", lang).format(
                member=result.member_name or t("scan.unknown_member", lang),
                event=result.event_title,
            )
        )
