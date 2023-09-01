import csv

from django.core.management import BaseCommand

from recipes.models import Tag


class Command(BaseCommand):

    def handle(self, *args, **options):

        with open('tags.csv', newline='', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                name = row[0]
                color = row[1]
                slug = row[2]
                tag = Tag(name=name,
                          color=color,
                          slug=slug)
                tag.save()

        print('Загрузил!')
