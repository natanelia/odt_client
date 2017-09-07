import rest_framework
import odt_client
from importlib import import_module
from . import settings
odt_models = import_module(settings.ODT_CLIENT_SYNC_MODULE)

class ReferenceField(rest_framework.serializers.Field):
    '''
    Reference object is serialized into 'key_label||key||value||value_label'
    '''

    
    def __init__(self, key_label, value_label, **kwargs):
        self.key_label = key_label
        self.value_label = value_label

        super(ReferenceField, self).__init__(**kwargs)
    

    def to_representation(self, value):
        if isinstance(value, odt_client.reference.ReferenceObject):
            return '%s||%s||%s||%s' % (value.key_label, value.key, value.value, value.value_label)
        elif isinstance(value, odt_client.reference.ValueRef):
            ref = odt_models.odt.models.TA_Reference.objects.get(
                key_label=self.key_label,
                value=value.value,
                value_label=self.value_label,
            )
            return '%s||%s||%s||%s' % (ref.key_label, ref.key, ref.value, ref.value_label)
        elif isinstance(value, odt_client.reference.KeyRef):
            ref = odt_models.odt.models.TA_Reference.objects.get(
                key_label=self.key_label,
                key=value.key,
                value_label=self.value_label,
            )
            return '%s||%s||%s||%s' % (ref.key_label, ref.key, ref.value, ref.value_label)
        elif isinstance(value, odt_client.reference.LabelRef):
            ref = odt_models.odt.models.TA_Reference.objects.get(
                key_label=self.key_label,
                value=value.value,
                value_label=value.value_label,
            )
            return '%s||%s||%s||%s' % (ref.key_label, ref.key, ref.value, ref.value_label)

    def to_internal_value(self, data):
        key_label, key, value, value_label = [c for c in data.split('||')]
        return odt_client.reference.ReferenceObject(key_label, key, value, value_label)