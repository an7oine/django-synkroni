# -*- coding: utf-8 -*-

from django.db import models


class SynkronoituvaMalli(models.Model):
  data = models.JSONField()

  class Meta:
    abstract = True
