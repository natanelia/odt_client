from django.conf import settings
import os.path

def get(key, default):
  return getattr(settings, key, default)

ODT_CLIENT_SYNC_URL = get('ODT_CLIENT_SYNC_URL', 'http://127.0.0.1:8000/odt/__model-sync__/')
ODT_CLIENT_SYNC_MODULE = get('ODT_CLIENT_SYNC_MODULE', 'odt_models')
ODT_CLIENT_SYNC_PATH = get('ODT_CLIENT_SYNC_PATH', os.path.dirname(os.path.realpath(settings.ROOT_URLCONF)) + '/' + ODT_CLIENT_SYNC_MODULE)
ODT_CLIENT_REFERENCE_IGNORE_MISSING_WARNING = get('ODT_REFERENCE_IGNORE_MISSING_WARNING', False)
ODT_CLIENT_SAVED_SYNC_FILE_NAME = get('ODT_CLIENT_SAVED_SYNC_FILE_NAME', '_last_model_sync.json')
ODT_CLIENT_CONFIG_FILENAME = get('ODT_CLIENT_CONFIG_FILENAME', 'odt_config.json')
ROOT_URLCONF = settings.ROOT_URLCONF  