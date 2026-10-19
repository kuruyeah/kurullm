from database import supabase


def get_active_conversation(telegram_id: int):
    response = (
        supabase
        .table("telegram_conversations")
        .select("*")
        .eq("telegram_id", telegram_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None

def create_conversation(
    telegram_id: int,
    telegram_chat_id: int,
    username: str | None,
    first_name: str |None,
):
    data = {
        "telegram_id": telegram_id,
        "telegram_chat_id": telegram_chat_id,
        "username": username,
        "first_name": first_name,
        "title": "New Chat",
        "is_active": True,
    }

    response = (
        supabase
        .table("telegram_conversations")
        .insert(data)
        .execute()
    )

    return response.data[0]

def ensure_active_conversation(
    telegram_id: int,
    telegram_chat_id: int,
    username: str | None,
    first_name: str | None,
):
    conversation = get_active_conversation(telegram_id)

    if conversation:
        return conversation

    return create_conversation(
        telegram_id=telegram_id,
        telegram_chat_id=telegram_chat_id,
        username=username,
        first_name=first_name,
    )




def deactivate_all_conversations(telegram_id: int):
    (
        supabase
        .table("telegram_conversations")
        .update(
            {
                "is_active": False
            }
        )
        .eq("telegram_id", telegram_id)
        .eq("is_active", True)
        .execute()
    )

def save_message(
    conversation_id: str,
    role: str,
    content: str,
    response_time_ms: int | None = None,
    is_fallback: bool = False,
    fallback_reason: str | None = None,
    is_handover: bool = False,
):
    data = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "response_time_ms": response_time_ms,
        "is_fallback": is_fallback,
        "fallback_reason": fallback_reason,
        "is_handover": is_handover,
    }

    response = (
        supabase
        .table("telegram_messages")
        .insert(data)
        .execute()
    )

    return response.data[0]





def add_message(
    conversation_id: str,
    role: str,
    content: str,
    response_time_ms: int | None = None,
    is_fallback: bool = False,
    fallback_reason: str | None = None,
    is_handover: bool = False,
):
    message = save_message(
       conversation_id=conversation_id,
    role=role,
    content=content,
    response_time_ms=response_time_ms,
    is_fallback=is_fallback,
    fallback_reason=fallback_reason,
    is_handover=is_handover,
    )

    update_conversation_stats(
    conversation_id,
    content,
)

    return message

def update_conversation_stats(
    conversation_id: str,
    last_message: str,
):
    supabase.rpc(
        "update_conversation_stats",
        {
            "conversation_uuid": conversation_id,
            "last_msg": last_message,
        },
    ).execute()

def update_conversation_title(
    conversation_id: str,
    title: str,
):
    response = (
        supabase
        .table("telegram_conversations")
        .update(
            {
                "title": title
            }
        )
        .eq("id", conversation_id)
        .execute()
    )

    return response.data[0]

def get_conversations(
    telegram_id: int,
    limit: int = 10,
):
    response = (
        supabase
        .table("telegram_conversations")
        .select("*")
        .eq("telegram_id", telegram_id)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )

    return response.data

def activate_conversation(
    conversation_id: str,
):
    response = (
        supabase
        .table("telegram_conversations")
        .update(
            {
                "is_active": True,
            }
        )
        .eq("id", conversation_id)
        .execute()
    )

    return response.data[0]

def get_conversation_by_index(
    telegram_id: int,
    index: int,
):
    conversations = (
        supabase
        .table("telegram_conversations")
        .select("*")
        .eq("telegram_id", telegram_id)
        .order("updated_at", desc=True)
        .execute()
    ).data

    if index < 1 or index > len(conversations):
        return None

    return conversations[index - 1]

def update_rating(
    message_id: str,
    rating: int,
):
    response = (
        supabase
        .table("telegram_messages")
        .update(
            {
                "rating": rating,
            }
        )
        .eq("id", message_id)
        .execute()
    )

    return response.data[0]