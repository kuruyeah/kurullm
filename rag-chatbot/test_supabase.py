from database import supabase

response = (
    supabase
    .table("telegram_conversations")
    .select("*")
    .limit(1)
    .execute()
)

print(response.data)