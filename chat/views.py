from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import ChatMessage

@login_required
def chat_support(request):
    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if message:
            chat_message = ChatMessage.objects.create(
                user=request.user,
                message=message
            )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # AJAX request
                return JsonResponse({
                    'success': True,
                    'message': chat_message.message,
                    'timestamp': chat_message.created_at.strftime("%b %d, %H:%M")
                })
            else:
                # Regular POST, redirect
                return redirect("chat_support")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Message cannot be empty.'})
            else:
                messages.error(request, "Message cannot be empty.")

    chat_messages = ChatMessage.objects.filter(user=request.user).order_by('created_at')
    return render(request, "chat/chat_widget.html", {
        "chat_messages": chat_messages
    })