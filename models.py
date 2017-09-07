from django_roa import Model as ROAModel
from django.db import models

class CommonROAModel(ROAModel):
    class Meta:
        abstract = True

    @classmethod
    def get_resource_url_list(cls):
        return u'http://127.0.0.1:8000/odt/api/%s/' % (cls.api_base_name)

    def get_resource_url_count(self):
        return self.get_resource_url_list()

class Reference(models.Model):
    key_label = models.TextField(blank=False, null=False, unique=False, max_length=128)
    key = models.TextField(blank=False, null=False, unique=False)
    value = models.TextField(blank=False, null=False, unique=False)
    value_label = models.TextField(blank=False, null=False, unique=False)

    class Meta:
        unique_together = (('key_label', 'key', 'value_label'))

    def __str__(self):
        return self.value
