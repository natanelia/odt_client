import sys
from django.apps import AppConfig
from .setup_utils.diff_check import DiffChecker

class ODTConfig(AppConfig):
    name = 'odt_client'
    verbose_name = 'ODT Client'
    def ready(self):
        dc = DiffChecker()
        dc.check()
        if dc.has_diff():
            print ('''
[ODT] ODT has detected model changes from the server. ::::
[ODT] Run "python manage.py odt_check_diff" to see changes. ::::
[ODT] Please run "python manage.py odt_generate_setup" to resync models ::::
''')

