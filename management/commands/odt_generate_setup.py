import os
import urllib2
import json
import copy
import pprint
from django.core.management.base import BaseCommand, CommandError
from odt_client.settings import *
from ...setup_utils.diff_check import DiffChecker

pp = pprint.PrettyPrinter(indent=2)

class Command(BaseCommand):

    def handle(self, *args, **options):
        config_filename = '%s/%s' % (os.path.dirname(os.path.realpath(settings.ROOT_URLCONF)), ODT_CLIENT_CONFIG_FILENAME)
        config = {}
        if os.path.isfile(config_filename):
            config_file = open(config_filename)
            config = json.load(config_file)
        else:
            raise Exception('ODT config file not found in %s.' % config_filename)

        res = urllib2.urlopen(ODT_CLIENT_SYNC_URL).read()

        models = json.loads(res)
        models = [m for m in models if config.get(m['full_name'], {}).get('_')]

        for m in models:

            model_path = m['class_path'].replace('.', '/')
            k = model_path.rfind('/')
            dir_path = '%s/%s' % (ODT_CLIENT_SYNC_PATH, model_path[:k])

            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            # create model file
            model_file = open('%s/%s.py' % (dir_path, model_path[k:]), 'w+')
            
            # write default model import
            model_file.write(
"""
from importlib import import_module
import django
import odt_models
from django.db import models
from rest_framework import serializers
from odt_client.models import CommonROAModel
from odt_client import serializers as odt_serializers

"""
            )

            if not m['class_path'].startswith('odt'):
                model_file.write('from odt_client.reference import ReferenceField\n')

            model_file.close()

        # create init files to make class importable
        init_file = open('%s/__init__.py' % ODT_CLIENT_SYNC_PATH, 'w+')
        init_file.close()

        for subdir, dirs, files in os.walk(ODT_CLIENT_SYNC_PATH):
            for dir in dirs:
                init_file = open('%s/__init__.py' % os.path.join(subdir, dir), 'w+')
                init_file.close()


        admin_classes_text = ''
        model_text_data = {}
        for m in models:

            model_path = m['class_path'].replace('.', '/')
            file_path = '%s/%s' % (ODT_CLIENT_SYNC_PATH, model_path)
            
            if file_path not in model_text_data.keys():
                model_text_data[file_path] = {}
            

            # write model classes
            class_text = 'class ODT_%s(CommonROAModel):\n' % m['class_name']
            class_text += '\t"""%s"""\n' % m['doc']
            class_text += '\tclass Meta:\n\t\tverbose_name = "%s"\n' % m['class_name']
            class_text += '\tapi_base_name = "%s/%s"\n\n' % (model_path, m['class_name'].lower())

            dependencies = []
            reference_fields = []
            fields_comma_seperated = []
            for f in m['fields']:
                if not config.get(m['full_name'], {}).get(f['name']):
                    continue

                if not f.get('relation', None):
                    if f['class_path'] == 'odt.reference' and f['class_name'] == 'ReferenceField':
                        class_text += (
'\t%s = ReferenceField("%s", "%s", help_text="%s")\n' % (
                            f['name'],
                            f['key_label'],
                            f['value_label'],
                            f['help_text'])
                        )

                        reference_fields.append(f)

                        fields_comma_seperated.append(f['name'])
                    elif f['class_name'] != 'AutoField':
                        class_text += (
'\t%s = %s.%s(max_length=%s, null=%s, blank=%s, help_text="%s"%s)\n' % (
                            f['name'],
                            f['class_path'],
                            f['class_name'],
                            '"%s"' % f['max_length'] if f.get('max_length', None) is not None else 'None',
                            f['null'],
                            True,
                            f['help_text'],
                            ', decimal_places=%d, max_digits=%d' % (f.get('decimal_places'), f.get('max_digits')) if f['class_name'] == 'DecimalField' else ''
)
                        )
                        fields_comma_seperated.append(f['name'])
                else:
                    related_model_full_name = '%s.%s' % (f['related_model_path'], f['related_model_name'])
                    if m['class_path'] != f['related_model_path']:
                        corr_rel = '%s.%s.ODT_%s' % (
                            ODT_CLIENT_SYNC_MODULE,
                            f['related_model_path'],
                            f['related_model_name'])
                    else:
                        corr_rel = '"ODT_%s"' % f['related_model_name']

                    class_text += (
'\t%s = %s.%s(%s, related_name=%s, null=%s, blank=%s, help_text="%s")\n' % (
                        f['name'],
                        f['class_path'],
                        f['class_name'],
                        corr_rel,
                        '"%s"' % f['related_name'] if f.get('related_name', None) is not None else 'None',
                        f['null'],
                        True,
                        f['help_text'].replace('"', "'"))
                    )
                    fields_comma_seperated.append(f['name'])

                    if related_model_full_name not in dependencies and m['class_path'] != f['related_model_path']:
                        dependencies.append(related_model_full_name)
                    elif f['related_model_name'] not in dependencies and m['class_path'] == f['related_model_path']:
                        if m['class_name'] != f['related_model_name']:
                            dependencies.append(f['related_model_name'])

#             class_text += (
# """
# \tdef __str__(self):
# \t\tr = ''
# """
#             )
#             for f in fields_comma_seperated:
#                 if f != 'created_at' and f != 'updated_at':
#                     class_text += '\t\tr += "%s, " % (self.' + f + ')\n'
#             class_text += '\t\treturn r\n'

            if m['str_func'][0][1].find('if six.PY2') == -1:
                for l in m['str_func'][0]:
                    class_text += '%s\n' % l.replace('\\t', '\t')

            class_text += (
"""
\t@classmethod
\tdef serializer(cls):
\t\treturn %sSerializer
""" % (m['class_name'])
            )

            class_text += (
"""
class %sSerializer(serializers.ModelSerializer):
\tclass Meta:
\t\tmodel = ODT_%s
\t\tfields = %s
""" % (m['class_name'], m['class_name'], tuple(fields_comma_seperated))
            )

            for rf in reference_fields:
                class_text += (
"""
\t%s = odt_serializers.ReferenceField("%s", "%s")
""" % (rf['name'], rf['key_label'], rf['value_label'])
                )

            class_text += ('\n\n')

            model_text_data[file_path][m['class_name']] = {
                'dependencies': dependencies,
                'text': class_text,
            }

            if fields_comma_seperated.__contains__('created_at'):
                fields_comma_seperated.remove('created_at')
            if fields_comma_seperated.__contains__('updated_at'):
                fields_comma_seperated.remove('updated_at')
            admin_classes_text += (
"""
class %sAdmin(admin.ModelAdmin):
\tlist_display = %s
\texclude = %s
""" % (m['class_name'], tuple(fields_comma_seperated), ('created_at', 'updated_at'))
            )

            if m['class_name'] == 'Reference':
                admin_classes_text += \
"""
\treadonly_fields = list_display
\tdef has_add_permision(self, request):
\t\treturn False

\tdef has_delete_permission(self, request, obj=None):
\t\treturn False
"""

        
        for file_path, model_data in model_text_data.iteritems():
            external_classes = []
            ordered_class_texts = []

            before_size = -1
            inserted_model_data = {}
            while len(model_data) > 0 and before_size != len(model_data):
                before_size = len(model_data)
                for c in inserted_model_data:
                    for k, k_data in model_data.items():
                        if c in k_data['dependencies']:
                            k_data['dependencies'].remove(c)
                
                for c, c_data in model_data.items():
                    if len(c_data['dependencies']) == 0:
                        ordered_class_texts.append(c_data['text'])
                        inserted_model_data[c] = model_data.pop(c, None)
            
            if len(model_data):
                for c, c_data in model_data.items():
                    for d in c_data['dependencies']:
                        if d not in external_classes:
                            external_classes.append(d)


                for c, c_data in model_data.items():
                    ordered_class_texts.append(c_data['text'])
                    inserted_model_data[c] = model_data.pop(c, None)

                # print '>>> %s' % file_path
                # for c, c_data in model_data.items():
                #     print '    FAILED TO OUTPUT %s WITH DEPS = %s' % (c, c_data['dependencies'])



            # create model file
            model_file = open('%s.py' % file_path, 'a')

            for ec in external_classes:
                k = ec.rfind('.')
                if k > -1:
                    model_file.write('from %s.%s import ODT_%s\n' % (ODT_CLIENT_SYNC_MODULE, ec[:k], ec[k+1:]))
            
            for oct in ordered_class_texts:
                model_file.write('%s\n' % oct)
            model_file.close()

        # WRITE ADMIN FILES
        admin_file = open('%s/admin.py' % (ODT_CLIENT_SYNC_PATH), 'w+')
        admin_file.write('from django.contrib import admin\n')

        for m in models:
            admin_file.write('from %s.%s import ODT_%s\n' % (ODT_CLIENT_SYNC_MODULE, m['class_path'], m['class_name']))

        admin_file.write(admin_classes_text)

        for m in models:
            admin_file.write('admin.site.register(ODT_%s, %sAdmin)\n' % (m['class_name'], m['class_name']))

        admin_file.close()

        print '[ODT] Interface setups are successfully done.'

        dc = DiffChecker()
        dc.check()
        if dc.has_diff():
            dc.print_check_result(open('odt_model_changes.txt', 'w+'))
            dc.print_check_result()

            saved_sync = open('%s/%s' % (os.path.dirname(os.path.realpath(settings.ROOT_URLCONF)), ODT_CLIENT_SAVED_SYNC_FILE_NAME), 'w+')
            saved_sync.write(res)
            saved_sync.close()
