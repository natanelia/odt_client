from django.core.management.base import BaseCommand, CommandError

from odt_client.metadata.core import MetaData

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('-i', '--input',
            action='store_true',
            dest='prompts_input',
            help='Prompts for user input')

        parser.add_argument('-c', '--complete',
            action='store_true',
            dest='complete',
            help='Get more complete version of meta-data')

        parser.add_argument('-m', '--model',
            dest='model_name',
            help='Find model with this name')
        
        parser.add_argument('-f', '--field',
            dest='field_name',
            help='Find model which contains this field name')
        
        parser.add_argument('-ht', '--help_text',
            dest='field_help_text',
            help='Find model which contains this field help text')

    def handle(self, *args, **options):
        model_name = options['model_name'] or ''
        field_name = options['field_name'] or ''
        field_help_text = options['field_help_text'] or ''

        if options['prompts_input']:
            model_name = raw_input('Model Name (any): ')
            field_name = raw_input('Field Name (any): ')
            field_help_text = raw_input('Field Help Text (any): ')

        models = MetaData.find_models(
            model_name=model_name, 
            field_name=field_name,
            field_help_text=field_help_text,
        )

        if len(models):

            for m in models:
                self.stdout.write(self.style.SQL_TABLE(m.full_name))

                self.stdout.write(m.doc)

                for field in m.get_fields():
                    f = field.serialize()

                    additional = []
                    if options['complete']:
                        if f.get('max_length', None):
                            additional.append('max_length=' + str(f.get('max_length', None)))
                        if f.get('decimal_places', None):
                            additional.append('decimal_places=' + str(f.get('decimal_places', None)))
                        if f.get('max_digits', None):
                            additional.append('max_digits=' + str(f.get('max_digits', None)))
                        if f.get('null', None):
                            additional.append('null=' + str(f.get('null', None)))
                        if f.get('blank', None):
                            additional.append('blank=' + str(f.get('blank', None)))
                        if f.get('default', None):
                            additional.append('default=' + str(f.get('default', None)))
                    if f.get('key_label', None):
                        additional.append('key_label=' + str(f.get('key_label', None)))
                    if f.get('value_label', None):
                        additional.append('value_label=' + str(f.get('value_label', None)))

                    # FIELD NAME
                    self.stdout.write('  %s - %s%s' % (
                        self.style.SQL_FIELD(field.name),
                        self.style.NOTICE(field.class_name),
                        self.style.NOTICE('(' + ', '.join(additional) + ')' if len(additional) else '')
                    ))

                    # import pprint
                    # pp = pprint.PrettyPrinter(indent=2)
                    # pp.pprint(field.field.__dict__)

                    # HELP TEXT
                    if field.help_text:
                        self.stdout.write(self.style.SQL_KEYWORD('   ? %s' % (field.help_text)))
                    
                    # RELATION
                    if field.relation:
                        self.stdout.write(self.style.SQL_COLTYPE('   %s %s' % (field.relation, field.related_model.full_name)))
                        
                self.stdout.write('\n')

            self.stdout.write(self.style.MIGRATE_HEADING('There are %d model(s) matching your query.' % len(models)))
        else:
            self.stdout.write(self.style.ERROR('Not Found.'))