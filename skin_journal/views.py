from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import JournalEntry
from .forms import JournalEntryForm
from users.models import Notification


@login_required
def journal_list(request):
    entries = JournalEntry.objects.filter(user=request.user)
    return render(request, "skin_journal/list.html", {"entries": entries})


@login_required
def journal_create(request):
    if request.method == "POST":
        form = JournalEntryForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            Notification.objects.create(
                user=request.user,
                message=f"Your journal entry for {entry.date} has been saved successfully."
            )
            messages.success(request, "Journal entry saved.")
            return redirect("skin_journal:list")
    else:
        form = JournalEntryForm()
    return render(request, "skin_journal/form.html", {"form": form, "action": "New Entry"})


@login_required
def journal_edit(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == "POST":
        form = JournalEntryForm(request.POST, request.FILES, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, "Entry updated.")
            return redirect("skin_journal:detail", pk=pk)
    else:
        form = JournalEntryForm(instance=entry)
    return render(request, "skin_journal/form.html", {"form": form, "action": "Edit Entry"})


@login_required
def journal_detail(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    return render(request, "skin_journal/detail.html", {"entry": entry})


@login_required
def journal_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == "POST":
        entry.delete()
        messages.success(request, "Entry deleted.")
        return redirect("skin_journal:list")
    return render(request, "skin_journal/confirm_delete.html", {"entry": entry})
