from django.db import models


class SiteStatus(models.Model):
    is_enabled = models.BooleanField(default=False)

    def __str__(self):
        return "Site Status"
