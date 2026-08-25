"""Typed content models for the Krisinformation API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
from typing import Any

_WHITESPACE = re.compile(r"\s+")


class _TextExtractor(HTMLParser):
    """Extract safe, readable text from API-provided HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"br", "div", "h1", "h2", "h3", "h4", "li", "p"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"div", "h1", "h2", "h3", "h4", "li", "p"}:
            self.parts.append(" ")


def html_to_text(value: Any) -> str:
    """Return normalized plain text for API HTML or text values."""
    if value is None:
        return ""
    parser = _TextExtractor()
    parser.feed(str(value))
    parser.close()
    return _WHITESPACE.sub(" ", "".join(parser.parts)).strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = _WHITESPACE.sub(" ", str(value)).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass(frozen=True, slots=True)
class ContentLink:
    """A related link supplied by Krisinformation."""

    text: str
    url: str

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> ContentLink:
        return cls(
            text=_optional_text(value.get("Text")) or "",
            url=_optional_text(value.get("Url")) or "",
        )

    def as_dict(self) -> dict[str, str]:
        return {"text": self.text, "url": self.url}


@dataclass(frozen=True, slots=True)
class ContentArea:
    """A geographic area assigned by Krisinformation."""

    type: str
    description: str

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> ContentArea:
        return cls(
            type=_optional_text(value.get("Type")) or "",
            description=_optional_text(value.get("Description")) or "",
        )

    def as_dict(self) -> dict[str, str]:
        return {"type": self.type, "description": self.description}


@dataclass(frozen=True, slots=True)
class NoticeLayout:
    """Visual metadata attached to a Krisinformation notice."""

    background_color: str | None
    icon: str | None
    right_aligned_icon: bool

    @classmethod
    def from_api(cls, value: dict[str, Any] | None) -> NoticeLayout:
        value = value or {}
        return cls(
            background_color=_optional_text(value.get("BackgroundColor")),
            icon=_optional_text(value.get("Icon")),
            right_aligned_icon=bool(value.get("RightAlignedIcon", False)),
        )

    def as_dict(self) -> dict[str, str | bool | None]:
        return {
            "background_color": self.background_color,
            "icon": self.icon,
            "right_aligned_icon": self.right_aligned_icon,
        }


def _links_from_api(value: Any) -> tuple[ContentLink, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(ContentLink.from_api(item) for item in value if isinstance(item, dict))


def _areas_from_api(value: Any) -> tuple[ContentArea, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(ContentArea.from_api(item) for item in value if isinstance(item, dict))


@dataclass(frozen=True, slots=True)
class NewsItem:
    """A normalized news article from Krisinformation."""

    identifier: str
    content_id: int | None
    content_type: str | None
    headline: str
    preamble: str
    body_text: str
    push_message: str | None
    published: datetime | None
    updated: datetime | None
    image_url: str | None
    web_url: str | None
    language: str | None
    event: str | None
    sender_name: str | None
    is_test: bool
    push: bool
    areas: tuple[ContentArea, ...]
    links: tuple[ContentLink, ...]

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> NewsItem:
        content_id = _optional_int(value.get("ContentId"))
        identifier = _optional_text(value.get("Identifier"))
        return cls(
            identifier=identifier
            or (str(content_id) if content_id is not None else ""),
            content_id=content_id,
            content_type=_optional_text(value.get("ContentTypeName")),
            headline=html_to_text(value.get("Headline")),
            preamble=html_to_text(value.get("Preamble")),
            body_text=html_to_text(value.get("BodyText")),
            push_message=_optional_text(value.get("PushMessage")),
            published=_parse_datetime(value.get("Published")),
            updated=_parse_datetime(value.get("Updated")),
            image_url=_optional_text(value.get("ImageLink")),
            web_url=_optional_text(value.get("Web")),
            language=_optional_text(value.get("Language")),
            event=_optional_text(value.get("Event")),
            sender_name=_optional_text(value.get("SenderName")),
            is_test=bool(value.get("IsTest", False)),
            push=bool(value.get("Push", False)),
            areas=_areas_from_api(value.get("Area")),
            links=_links_from_api(value.get("Links")),
        )

    @property
    def sort_datetime(self) -> datetime:
        return (
            self.updated or self.published or datetime.min.replace(tzinfo=timezone.utc)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "content_id": self.content_id,
            "content_type": self.content_type,
            "headline": self.headline,
            "preamble": self.preamble,
            "body_text": self.body_text,
            "push_message": self.push_message,
            "published": _serialize_datetime(self.published),
            "updated": _serialize_datetime(self.updated),
            "image_url": self.image_url,
            "web_url": self.web_url,
            "language": self.language,
            "event": self.event,
            "sender_name": self.sender_name,
            "is_test": self.is_test,
            "push": self.push,
            "areas": [area.as_dict() for area in self.areas],
            "links": [link.as_dict() for link in self.links],
        }


@dataclass(frozen=True, slots=True)
class NoticeItem:
    """A normalized notice from Krisinformation."""

    identifier: str
    content_id: int | None
    content_type: str | None
    notice_type: int | None
    headline: str
    preamble: str
    body_text: str
    mobile_body: str
    changed: datetime | None
    image_url: str | None
    image_caption: str | None
    video_url: str | None
    video_caption: str | None
    youtube_id: str | None
    sort_order: int | None
    layout: NoticeLayout
    areas: tuple[ContentArea, ...]
    links: tuple[ContentLink, ...]

    @classmethod
    def from_api(cls, value: dict[str, Any]) -> NoticeItem:
        content_id = _optional_int(value.get("ContentId"))
        identifier = _optional_text(value.get("Id"))
        return cls(
            identifier=identifier
            or (str(content_id) if content_id is not None else ""),
            content_id=content_id,
            content_type=_optional_text(value.get("ContentTypeName")),
            notice_type=_optional_int(value.get("NoticeType")),
            headline=html_to_text(value.get("Headline")),
            preamble=html_to_text(value.get("Preamble")),
            body_text=html_to_text(value.get("BodyText")),
            mobile_body=html_to_text(value.get("MobileBody")),
            changed=_parse_datetime(value.get("ChangedDate")),
            image_url=_optional_text(value.get("ImageLink")),
            image_caption=_optional_text(value.get("ImageCaption")),
            video_url=_optional_text(value.get("VideoUrl")),
            video_caption=_optional_text(value.get("VideoCaption")),
            youtube_id=_optional_text(value.get("YoutubeId")),
            sort_order=_optional_int(value.get("SortOrder")),
            layout=NoticeLayout.from_api(
                value.get("Layout") if isinstance(value.get("Layout"), dict) else None
            ),
            areas=_areas_from_api(value.get("Area")),
            links=_links_from_api(value.get("Links")),
        )

    @property
    def sort_datetime(self) -> datetime:
        return self.changed or datetime.min.replace(tzinfo=timezone.utc)

    @property
    def is_smhi_weather_warning(self) -> bool:
        """Return whether Krisinformation identifies this as an SMHI warning."""
        return bool(
            self.layout.icon and self.layout.icon.casefold().startswith("warning_smhi_")
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "identifier": self.identifier,
            "content_id": self.content_id,
            "content_type": self.content_type,
            "notice_type": self.notice_type,
            "headline": self.headline,
            "preamble": self.preamble,
            "body_text": self.body_text,
            "mobile_body": self.mobile_body,
            "changed": _serialize_datetime(self.changed),
            "image_url": self.image_url,
            "image_caption": self.image_caption,
            "video_url": self.video_url,
            "video_caption": self.video_caption,
            "youtube_id": self.youtube_id,
            "sort_order": self.sort_order,
            "is_smhi_weather_warning": self.is_smhi_weather_warning,
            "layout": self.layout.as_dict(),
            "areas": [area.as_dict() for area in self.areas],
            "links": [link.as_dict() for link in self.links],
        }
