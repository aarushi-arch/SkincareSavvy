from django.db import models
from django.contrib.auth.models import User


def journal_image_path(instance, filename):
    return f"journal/{instance.user.id}/{filename}"


class JournalEntry(models.Model):
    SKIN_CHOICES = [
        ("clear",      "✨ Clear"),
        ("oily",       "💧 Oily"),
        ("dry",        "🌵 Dry"),
        ("breakout",   "🔴 Breakout"),
        ("sensitive",  "🌸 Sensitive"),
        ("combination","🔀 Combination"),
    ]

    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name="journal_entries")
    date           = models.DateField()
    skin_condition = models.CharField(max_length=20, choices=SKIN_CHOICES, blank=True)
    notes          = models.TextField(blank=True)
    products_used  = models.TextField(blank=True, help_text="Comma-separated product names")
    image          = models.ImageField(upload_to=journal_image_path, blank=True, null=True)

    # Skin concern severity (1 = mild, 5 = severe, 0 = not present)
    acne_severity       = models.PositiveSmallIntegerField(default=0)
    dark_spots_severity = models.PositiveSmallIntegerField(default=0)
    wrinkles_severity   = models.PositiveSmallIntegerField(default=0)

    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        unique_together = ["user", "date"]

    def __str__(self):
        return f"{self.user.username} — {self.date}"

    @property
    def products_list(self):
        return [p.strip() for p in self.products_used.split(",") if p.strip()]
