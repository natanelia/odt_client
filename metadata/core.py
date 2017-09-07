from django.db.models import get_app, get_models
from odt_client import settings
from odt_client.metadata.info import ModelInfo, FieldInfo
from odt_client.models import CommonROAModel

class MetaData(object):
    @staticmethod
    def all_models():
        models = []
        from odt_client.models import CommonROAModel
        for model in vars()['CommonROAModel'].__subclasses__():
            models.append(ModelInfo(model))

        return models

    @staticmethod
    def find_models(model_name='', field_name='', field_help_text=''):
        model_name = model_name or ''
        field_name = field_name or ''
        field_help_text = field_help_text or ''

        models = MetaData.all_models()
        models_filtered_by_model_name = []
        models_filtered_by_field_name = []
        models_filtered_by_field_help_text = []
        result = models

        if model_name != '':
            for m in result:
                if m.full_name.lower().find(model_name.lower()) > -1:
                    models_filtered_by_model_name.append(m)
            
            result = models_filtered_by_model_name
        
        if field_name != '':
            for m in result:
                for field in m.get_fields():
                    if field.name.lower().find(field_name.lower()) > - 1:
                        models_filtered_by_field_name.append(m)
        
            result = models_filtered_by_field_name    
        
        if field_help_text != '':
            for m in result:
                for field in m.get_fields():
                    if field.help_text:
                        if field.help_text.lower().find(field_help_text.lower()) > - 1:
                            models_filtered_by_field_help_text.append(m)
        
            result = models_filtered_by_field_help_text               

        return result