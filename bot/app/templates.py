def lead_card_text(brand: str, city: str, summary: str, phone: str = "") -> str:
    """Форматирует карточку лида для отправки в Telegram."""
    lines = []
    if phone:
        lines.append(f"📱 <code>{phone}</code>")
    lines.append(f"📍 {city}")
    lines.append(f"🚗 <b>{brand}</b>")
    lines.append(f"💬 {summary}")
    return "\n".join(lines)


def contact_opened_text(phone: str, recording_url: str | None = None) -> str:
    """Форматирует сообщение с открытым контактом."""
    lines = [f"✅ Контакт открыт\n\n📱 <code>{phone}</code>"]
    if recording_url:
        lines.append(f"\n🎧 <a href=\"{recording_url}\">Прослушать запись</a>")
    return "\n".join(lines)
