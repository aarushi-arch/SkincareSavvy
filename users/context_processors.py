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
