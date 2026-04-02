def lead_card_text(
    client_name: str = "",
    phone: str = "",
    country_origin: str = "",
    city: str = "",
    timing: str = "",
) -> str:
    """Форматирует карточку лида для отправки в Telegram."""
    lines = []
    if client_name:
        lines.append(f"👤 {client_name}")
    if phone:
        lines.append(f"📱 <code>{phone}</code>")
    if country_origin:
        lines.append(f"🌏 {country_origin}")
    if city:
        lines.append(f"📍 {city}")
    if timing:
        lines.append(f"⏱ {timing}")
    return "\n".join(lines)


def contact_opened_text(phone: str, recording_url: str | None = None) -> str:
    """Форматирует сообщение с открытым контактом."""
    lines = [f"✅ Контакт открыт\n\n📱 <code>{phone}</code>"]
    if recording_url:
        lines.append(f"\n🎧 <a href=\"{recording_url}\">Прослушать запись</a>")
    return "\n".join(lines)
