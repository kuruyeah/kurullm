from services.telegram_service import (
    ensure_active_conversation,
    update_last_message,
)

conversation = ensure_active_conversation(
    telegram_id=123456789,
    telegram_chat_id=123456789,
    username="erlan_test",
    first_name="Erlan",
)

update_last_message(
    conversation["id"],
    "Halo ini pesan terakhir"
)

print("Success")