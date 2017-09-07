from django.db.models import Model
from django.db.models.fields import Field

import inspect

class ModelInfo(object):
    def __init__(self, model, **kwargs):
        self.model = model
        self.name = model.__name__
        self.class_name = model.__name__
        self.class_path = model.__module__
        self.doc = model.__doc__
        self.full_name = '%s.%s' % (self.class_path, self.class_name)

        super(ModelInfo, self).__init__(**kwargs)
    
    def get_fields(self):
        field_infos = []
        for field in self.model._meta.get_fields():
            field_infos.append(FieldInfo(field))
        return field_infos

    def get_serialized_fields(self):
        field_infos = []
        for f in self.get_fields():
            field_infos.append(f.serialize())
        return field_infos

    def serialize(self):
        return {
            'name': self.name,
            'full_name': self.full_name,
            'class_name': self.class_name,
            'class_path': self.class_path,
        }

    def serialize_with_fields(self):
        m = self.serialize()
        m['fields'] = []
        fields = self.get_fields()
        for f in fields:
            m['fields'].append(f.serialize())
        return m


class FieldInfo(object):
    def __init__(self, field, **kwargs):
        self.field = field
        self.name = field.name
        self.class_name = field.__class__.__name__
        self.class_path = field.__class__.__module__
        self.__doc__ = field.__doc__
        self.model = field.model
        self.help_text = None
        self.relation = None
        self.related_model = None
        
        if hasattr(field, 'help_text'):
            self.help_text = field.help_text

        if field.is_relation and field.related_model is not None:
            if field.many_to_many:
                self.relation = '*..*'
            elif field.many_to_one:
                self.relation = '*..1'
            elif field.one_to_many:
                self.relation = '1..*'
            elif field.one_to_one:
                self.relation = '1..1'

            self.related_model = ModelInfo(field.related_model)

        super(FieldInfo, self).__init__(**kwargs)

    def serialize(self):
        r = {
            'name': self.name,
            'class_name': self.class_name,
            'class_path': self.class_path,
            'help_text': unicode(self.help_text),
            'relation': self.relation,
            'model_name': self.model.__name__,
        }

        if self.related_model:
            r['related_model_name'] = self.related_model.class_name
            r['related_model_path'] = self.related_model.class_path
        
        if hasattr(self.field, 'rel'):
            if self.field.rel is not None:
                r['related_name'] = self.field.rel.related_name

                if self.relation == '*..*':
                    r['through'] = '%s.%s' % (self.field.rel.through.__module__, self.field.rel.through.__name__)
                    r['through_fields'] = self.field.rel.through_fields

        r['max_length'] = getattr(self.field, 'max_length', None)
        r['null'] = getattr(self.field, 'null', None)
        r['blank'] = getattr(self.field, 'blank', None)
        r['decimal_places'] = getattr(self.field, 'decimal_places', None)
        r['max_digits'] = getattr(self.field, 'max_digits', None)

        default = getattr(self.field, 'default', None)
        if default:
            if not inspect.isclass(default) and not inspect.isfunction(default):
                r['default'] = default

        if self.class_path == 'odt.reference' and self.class_name == 'ReferenceField':
            r['key_label'] = self.field.key_label
            r['value_label'] = self.field.value_label

        for k, v in r.items():
            if v is None:
                del r[k]

        return r