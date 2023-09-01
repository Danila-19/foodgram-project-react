import csv

from django.core.management import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):

    def handle(self, *args, **options):

        with open('ingredients.csv', newline='', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                name = row[0]
                measurement_unit = row[1]
                ingredient = Ingredient(name=name,
                                        measurement_unit=measurement_unit)
                ingredient.save()

        print('Загрузил!')
