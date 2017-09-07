import sys
import os
import urllib2
import json
import copy
import pprint
from django.core.management.base import BaseCommand, CommandError
from odt_client.settings import *

UNKNOWN = '_unknown_'

class DiffChecker(object):
    result = None

    def check(self):
        res = urllib2.urlopen(ODT_CLIENT_SYNC_URL).read()
        new = json.loads(res)

        old_sync_full_name = '%s/%s' % (os.path.dirname(os.path.realpath(settings.ROOT_URLCONF)), ODT_CLIENT_SAVED_SYNC_FILE_NAME)
        if os.path.isfile(old_sync_full_name):
            old_sync_file = open(old_sync_full_name)
            old = json.load(old_sync_file)

            new_map = self.convert_models_to_dict(new)
            old_map = self.convert_models_to_dict(old)

            self.result = self.check_models(old_map, new_map)
        else:
            self.result = None

    def has_diff(self):
        if self.result:
            return len(self.result['missing_in_new_map']) or \
            len(self.result['missing_in_old_map']) or \
            len(self.result['model_mismatches'])
        else:
            return True

    def convert_models_to_dict(self, models):
        mapper = {}
        for model in models:
            mapper[model['full_name']] = model
        return mapper

    def convert_fields_to_dict(self, fields):
        mapper = {}
        for field in fields:
            mapper[field['name']] = field
        return mapper

    def check_models(self, old_map, new_map):
        missing_in_new_map = []
        missing_in_old_map = []
        model_mismatches = []

        for k, v in old_map.items():
            if new_map.get(k, None) is None:
                missing_in_new_map.append(k)
            else:
                model_check_result = self.check_model(v, new_map.get(k, {}))
                if len(model_check_result['missing_in_new_model']) > 0 or \
                len(model_check_result['missing_in_old_model']) > 0 or \
                len(model_check_result['value_not_match']) > 0 or \
                len(model_check_result['field_checks']['missing_in_new_fields']) > 0 or \
                len(model_check_result['field_checks']['missing_in_old_fields']) > 0 or \
                len(model_check_result['field_checks']['field_mismatches']) > 0:
                    model_mismatches.append((v['full_name'], model_check_result,))
        
        for k, v in new_map.items():
            if old_map.get(k, None) is None:
                missing_in_old_map.append(k)

        return {
            'missing_in_new_map' : missing_in_new_map,
            'missing_in_old_map' : missing_in_old_map,
            'model_mismatches' : model_mismatches,
        }

    def check_model(self, old_model, new_model):
        missing_in_new_model = []
        missing_in_old_model = []
        value_not_match = []

        for k, v in old_model.items():
            if k != 'fields':
                if new_model.get(k, UNKNOWN) == UNKNOWN:
                    missing_in_new_model.append(k)
                elif new_model.get(k, UNKNOWN) != v:
                    value_not_match.append((k, v, new_model.get(k, UNKNOWN),))
        
        for k, v in new_model.items():
            if k != 'fields':
                if old_model.get(k, UNKNOWN) == UNKNOWN:
                    missing_in_old_model.append(k)

        return {
            'missing_in_new_model' : missing_in_new_model,
            'missing_in_old_model' : missing_in_old_model,
            'value_not_match' : value_not_match,
            'field_checks' : self.check_fields(
                self.convert_fields_to_dict(old_model.get('fields', [])),
                self.convert_fields_to_dict(new_model.get('fields', []))
            ),
        }


    def check_fields(self, old_fields, new_fields):
        missing_in_new_fields = []
        missing_in_old_fields = []
        field_mismatches = []

        for k, v in old_fields.items():
            if new_fields.get(k, None) is None:
                missing_in_new_fields.append(k)
            else:
                field_check_result = self.check_field(v, new_fields.get(k, {}))
                if len(field_check_result['missing_in_new_field']) > 0 or \
                len(field_check_result['missing_in_old_field']) > 0 or \
                len(field_check_result['value_not_match']) > 0:
                    field_mismatches.append((v['name'], field_check_result,))
        
        for k, v in new_fields.items():
            if old_fields.get(k, None) is None:
                missing_in_old_fields.append(k)

        return {
            'missing_in_new_fields' : missing_in_new_fields,
            'missing_in_old_fields' : missing_in_old_fields,
            'field_mismatches' : field_mismatches,
        }

    def check_field(self, old_field, new_field):
        missing_in_new_field = []
        missing_in_old_field = []
        value_not_match = []

        for k, v in old_field.items():
            if new_field.get(k, UNKNOWN) == UNKNOWN:
                missing_in_new_field.append(k)
            elif new_field.get(k, UNKNOWN) != v:
                value_not_match.append((k, v, new_field.get(k, UNKNOWN),))
        
        for k, v in new_field.items():
            if old_field.get(k, UNKNOWN) == UNKNOWN:
                missing_in_old_field.append(k)

        return {
            'missing_in_new_field' : missing_in_new_field,
            'missing_in_old_field' : missing_in_old_field,
            'value_not_match' : value_not_match,
        }

    def print_check_result(self, stdout=sys.stdout):
        '''
            check_result = {
                'missing_in_new_map' : [model_full_name1, model_full_name2, ...],
                'missing_in_old_map' : [model_full_name1, model_full_name2, ...],
                'model_mismatches' : [(model_full_name1, {
                    'missing_in_new_model' : [k1, k2, ...],
                    'missing_in_old_model' : [k1, k2, ...],
                    'value_not_match' : [(k1, vOld1, vNew1), (k2, vOld2, vNew2), ...]
                    'field_checks' : {... similar to model_mismatches array}
                },), ...],
            }
        '''
        check_result = self.result
        if self.has_diff():
            if check_result is None:
                print >> stdout, '[ODT] Models has never been synced yet.'
                return None

            if len(check_result['missing_in_new_map']):
                print >> stdout, 'REMOVED MODELS -------------------------'
                for model_full_name in check_result['missing_in_new_map']:
                    print >> stdout, '- %s' % model_full_name
                

            if len(check_result['missing_in_old_map']):
                print >> stdout, 'NEW MODELS -------------------------'
                for model_full_name in check_result['missing_in_old_map']:
                    print >> stdout, '- %s' % model_full_name

            if len(check_result['model_mismatches']):
                print >> stdout, 'MODIFIED MODELS -------------------------'
                for mfn, mcr in check_result['model_mismatches']:
                    print >> stdout, '- %s' % mfn

                    if len(mcr['missing_in_new_model']):
                        print >> stdout, '\tIs Not Defined Any Longer ---'
                        for model_full_name in mcr['missing_in_new_model']:
                            print >> stdout, '\t- %s' % model_full_name
                        

                    if len(mcr['missing_in_old_model']):
                        print >> stdout, '\tIs Now Defined ---'
                        for model_full_name in mcr['missing_in_old_model']:
                            print >> stdout, '\t- %s' % model_full_name

                    if len(mcr['value_not_match']):
                        print >> stdout, '\tIs Updated ---'
                        for k, v_old, v_new in mcr['value_not_match']:
                            print >> stdout, '\t- %s : OLD(%s) - NEW(%s)' % (k, v_old, v_new)
                    
                    fc = mcr['field_checks']
                    if len(fc['missing_in_new_fields']) or \
                    len(fc['missing_in_old_fields']) or \
                    len(fc['field_mismatches']):
                        if len(fc['missing_in_new_fields']):
                            print >> stdout, '\tRemoved Fields ---'
                            for field_full_name in fc['missing_in_new_fields']:
                                print >> stdout, '\t- %s' % field_full_name
                            

                        if len(fc['missing_in_old_fields']):
                            print >> stdout, '\tNew Fields ---'
                            for field_full_name in fc['missing_in_old_fields']:
                                print >> stdout, '\t- %s' % field_full_name

                        if len(fc['field_mismatches']):
                            print >> stdout, '\tModified Fields ---'
                            for mfn, mcr in fc['field_mismatches']:
                                print >> stdout, '\t- %s' % mfn

                                if len(mcr['missing_in_new_field']):
                                    print >> stdout, '\t\tIs Not Defined Any Longer -'
                                    for field_full_name in mcr['missing_in_new_field']:
                                        print >> stdout, '\t\t- %s' % field_full_name
                                    

                                if len(mcr['missing_in_old_field']):
                                    print >> stdout, '\t\tIs Now Defined -'
                                    for field_full_name in mcr['missing_in_old_field']:
                                        print >> stdout, '\t\t- %s' % field_full_name

                                if len(mcr['value_not_match']):
                                    print >> stdout, '\t\tIs Updated -'
                                    for k, v_old, v_new in mcr['value_not_match']:
                                        print >> stdout, '\t\t- %s : OLD(%s) - NEW(%s)' % (k, v_old, v_new)
        else:
            print >> stdout, '[ODT] Model check concludes without changes.'