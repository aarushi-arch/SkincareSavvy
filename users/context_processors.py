from chat.models import ChatMessage

def notifications_processor(request):
    """Context processor to provide unread notifications to all templates."""
    if request.user.is_authenticated:
        unread_notifications = request.user.notifications.filter(is_read=False)[:5]
        unread_notifications_count = request.user.notifications.filter(is_read=False).count()
        return {
            'unread_notifications': unread_notifications,
            'unread_count': unread_notifications_count
        }
    return {
        'unread_notifications': [],
        'unread_count': 0
    }

def chat_messages_processor(request):
    """Context processor to provide chat messages for the widget."""
    if request.user.is_authenticated:
        messages = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:10]  # last 10 messages
        return {
            'chat_messages': messages
        }
    return {
        'chat_messages': []
    }
