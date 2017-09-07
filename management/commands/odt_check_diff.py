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
        dc = DiffChecker()
        dc.check()
        if dc.has_diff():
            print '''
[ODT] ODT has detected model changes from the server. ::::
[ODT] Please run "python manage.py odt_generate_setup" to resync models ::::

'''
        
        dc.print_check_result()
