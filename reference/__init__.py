import warnings
from importlib import import_module

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from django.db import models

from odt_client import settings
Reference = import_module(settings.ODT_CLIENT_SYNC_MODULE + '.odt.models').ODT_Reference

CUSTOM_REF_SPLITTER = '|'

class ReferenceObject(object):
    def __init__(self, key_label, key, value=None, value_label=None, in_db=False, *args, **kwargs):
        self.key_label = key_label
        self.key = key
        self.value = value or key
        self.value_label = value_label or key_label
        self.in_db = in_db

        super(ReferenceObject, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.value

    def check_in_db(self):
        try:
            Reference.objects.get(
                key_label=self.key_label,
                key=self.key)

            self.in_db = True
        except ObjectDoesNotExist:
            self.in_db = False
        except Reference.MultipleObjectsReturned:
            self.in_db = True

        return self.in_db

    def save(self):
        ref, created = Reference.objects.get_or_create(key_label=self.key_label, key=self.key, value_label=self.value_label)
        if not created:
            ref.value = self.value
            ref.save()

    def create(self):
        Reference.objects.create(key_label=self.key_label, key=self.key, value=self.value, value_label=self.value_label)
    
    def convertTo(self, value_label):
        try:
            to_ref = Reference.objects.get(key_label=self.key_label, key=self.key, value_label=value_label)
            self = ReferenceObject(
                self.key_label,
                self.key,
                to_ref.value,
                value_label
            )
        except Reference.DoesNotExist:
            if not settings.ODT_CLIENT_REFERENCE_IGNORE_MISSING_WARNING:
                warnings.warn('DoesNotExist: Reference with key_label="%s", key="%s", value_label="%s" is missing. Returning fallback reference.' % (self.key_label, self.key, value_label), RuntimeWarning)
            
            self = ReferenceObject(
                self.key_label,
                self.key,
                self.key,
                self.key_label,
            )

        return self

class ReferenceField(models.TextField):
    description = _("Field containing reference value that is linked to a reference table")

    def __init__(self, key_label, value_label, *args, **kwargs):
        self.key_label = key_label
        self.value_label = value_label

        super(ReferenceField, self).__init__(*args, **kwargs)

    def parse_ref(self, key):
        try:
            dbref = Reference.objects.get(
                key_label=self.key_label,
                value_label=self.value_label,
                key=key)
            return ReferenceObject(self.key_label, key, dbref.value, self.value_label, in_db=True)
        except ObjectDoesNotExist:
            if not settings.ODT_CLIENT_REFERENCE_IGNORE_MISSING_WARNING:
                warnings.warn('DoesNotExist: Reference with key_label="%s", key="%s", value_label="%s" is missing. Returning fallback reference.' % (self.key_label, key, self.value_label), RuntimeWarning)
            return ReferenceObject(self.key_label, key, key, self.key_label, in_db=False)

    def parse_value(self, value):
        try:
            dbref = Reference.objects.get(
                key_label=self.key_label,
                value_label=self.value_label,
                value=value)
            return ReferenceObject(self.key_label, dbref.key, value, self.value_label, in_db=True)
        except ObjectDoesNotExist:
            if not settings.ODT_CLIENT_REFERENCE_IGNORE_MISSING_WARNING:
                warnings.warn('DoesNotExist: Reference with key_label="%s", value="%s", value_label="%s" is missing. Returning fallback reference.' % (self.key_label, value, self.value_label), RuntimeWarning)
            # return ReferenceObject(self.key_label, key, key, self.key_label, in_db=False)
            raise Exception('DoesNotExist: Reference with key_label="%s", value="%s", value_label="%s" is missing. Returning fallback reference.' % (self.key_label, value, self.value_label))

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        return self.parse_ref(value)

    def to_python(self, value):
        if value is None:
            return value

        return self.parse_value(value)

    def get_prep_value(self, value):
        '''
            https://docs.djangoproject.com/en/1.11/howto/custom-model-fields/#converting-python-objects-to-query-values
            value:
                ValueRef(value) > Direct value access according to predefined key_label and value_label
                KeyRef(key) > Key access according to predefined key_label
                LabelRef(value_label, value) > Get corresponding reference by value and custom label
        '''
        ref = value
        if not isinstance(value, Reference):
            if isinstance(value, ValueRef):
                ref = Reference.objects.get(
                    key_label=self.key_label,
                    value=value.value,
                    value_label=self.value_label,
                )
                return ref.key
            elif isinstance(value, KeyRef):
                ref = Reference.objects.get(
                    key_label=self.key_label,
                    key=value.key,
                )
                return ref.key
            elif isinstance(value, LabelRef):
                ref = Reference.objects.get(
                    key_label=self.key_label,
                    value=value.value,
                    value_label=value.value_label,
                )
                return ref.key
            elif isinstance(value, basestring) or hasattr(value, 'key'):
                if isinstance(value, basestring):
                    if CUSTOM_REF_SPLITTER in value:
                        splitted_value = value.split(CUSTOM_REF_SPLITTER)
                        ref_type = splitted_value[0]

                        if ref_type == 'ValueRef':
                            v = splitted_value[1]
                            ref = Reference.objects.get(
                                key_label=self.key_label,
                                value=v,
                                value_label=self.value_label,
                            )
                            key = ref.key
                        elif ref_type == 'KeyRef':
                            k = splitted_value[1]
                            ref = Reference.objects.get(
                                key_label=self.key_label,
                                key=k,
                            )
                            key = ref.key
                        elif ref_type == 'LabelRef':
                            vl = splitted_value[1]
                            v = splitted_value[2]
                            ref = Reference.objects.get(
                                key_label=self.key_label,
                                value=v,
                                value_label=vl,
                            )
                            key = ref.key
                    else:
                        ref = Reference.objects.get(
                            key_label=self.key_label,
                            value=value,
                            value_label=self.value_label,
                        )
                        key = ref.key
                        print key
                else:
                    key = value.key

                    if value.key_label != self.key_label:
                        raise ValidationError(_('Reference key_label mismatch.'))

                ref = ReferenceObject(self.key_label, key)
                if not ref.check_in_db():
                    raise ObjectDoesNotExist('Reference with key_label="%s" and key=:%s: is missing.' % (self.key_label, key))
                
                return key
            else:
                raise ValidationError(_('Invalid object "%s" given.' % value.__class__))
                return None

    def deconstruct(self):
        field_class = "django.db.models.TextField"
        name, path, args, kwargs = super (ReferenceField, self).deconstruct()
        return name, field_class, args, kwargs


class ValueRef(object):
    def __init__(self, value, *args, **kwargs):
        self.value = value
        super(ValueRef, self).__init__(*args, **kwargs)
    
    def __str__(self):
        return '%s%s%s' % ('ValueRef', CUSTOM_REF_SPLITTER, self.value)

class KeyRef(object):
    def __init__(self, key, *args, **kwargs):
        self.key = key
        super(KeyRef, self).__init__(*args, **kwargs)

    def __str__(self):
        return '%s%s%s' % ('KeyRef', CUSTOM_REF_SPLITTER, self.key)

class LabelRef(object):
    def __init__(self, value_label, value, *args, **kwargs):
        self.value_label = value_label
        self.value = value
        super(LabelRef, self).__init__(*args, **kwargs)  

    def __str__(self):
        return '%s%s%s%s%s' % ('LabelRef', CUSTOM_REF_SPLITTER, self.value_label, CUSTOM_REF_SPLITTER, self.value)