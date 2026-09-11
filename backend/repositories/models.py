import uuid
from django.conf import settings
from django.db import models

class Repository(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=220)
    default_branch = models.CharField(max_length=200, default='main')
    github_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner','github_id'], name='unique_owner_repo')]
