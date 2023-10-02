from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


User = get_user_model()


MIN_AMOUNT_OR_COOKING_TIME = 1
MAX_AMOUNT_OR_COOKING_TIME = 32000


def validate_amount(value):
    if value < MIN_AMOUNT_OR_COOKING_TIME:
        raise ValidationError(
            'Количество должно быть больше '
            'минимального значения.')
    if value > MAX_AMOUNT_OR_COOKING_TIME:
        raise ValidationError(
            'Количество не должно превышать '
            'максимального значения.')


def validate_cooking_time(value):
    if value < MIN_AMOUNT_OR_COOKING_TIME:
        raise ValidationError(
            'Время приготовления должно быть больше указанного '
            'минимального значения.')
    if value > MAX_AMOUNT_OR_COOKING_TIME:
        raise ValidationError(
            'Время приготовления не должно превышать указанного '
            'максимального значения.')


class Tag(models.Model):
    name = models.CharField(max_length=200, verbose_name='Наименование')
    color = models.CharField(max_length=7, verbose_name='Цвет')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='Slug')

    class Meta:
        verbose_name = 'Тэги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=200, verbose_name='Наименование')
    measurement_unit = models.CharField(max_length=200,
                                        verbose_name='Единица измерения')

    class Meta:
        verbose_name = 'Ингредиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               related_name='recipes',
                               verbose_name='Автор')
    name = models.CharField(max_length=200, verbose_name='Наименование')
    image = models.ImageField(upload_to='media/', verbose_name='Изображение')
    text = models.CharField(max_length=2000, verbose_name='Текст')
    ingredients = models.ManyToManyField(Ingredient,
                                         through='RecipeIngredient',
                                         related_name='recipes',
                                         verbose_name='Ингредиенты')
    tags = models.ManyToManyField(Tag,
                                  related_name='recipes',
                                  verbose_name='Теги')
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[validate_cooking_time])
    pub_date = models.DateTimeField(auto_now=True,
                                    verbose_name='Дата публикации')

    class Meta:
        verbose_name = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe,
                               on_delete=models.CASCADE,
                               related_name='recipe_ingredients',
                               verbose_name='Рецепт')
    ingredient = models.ForeignKey(Ingredient,
                                   on_delete=models.CASCADE,
                                   related_name='recipe_ingredients',
                                   verbose_name='Ингредиент')
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[validate_amount])

    def __str__(self):
        return f'{self.ingredient.name} ({self.amount})'


class ShoppingCart(models.Model):
    recipe = models.ForeignKey(Recipe,
                               related_name='carts',
                               on_delete=models.CASCADE,
                               verbose_name='Рецепт')
    user = models.ForeignKey(User,
                             related_name='cart',
                             on_delete=models.CASCADE,
                             verbose_name='Пользователь')

    class Meta:
        verbose_name = 'Список покупок'

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'


class Favorite(models.Model):
    recipe = models.ForeignKey(Recipe,
                               related_name='favored_by',
                               on_delete=models.CASCADE,
                               verbose_name='Рецепт')
    user = models.ForeignKey(User,
                             related_name='favorite_recipes',
                             on_delete=models.CASCADE,
                             verbose_name='Пользователь')
    pub_date = models.DateTimeField(verbose_name='Дата добавления',
                                    auto_now_add=True)

    class Meta:
        verbose_name = 'Избранное'

    def __str__(self):
        return f'{self.user.username} - {self.recipe.name}'
