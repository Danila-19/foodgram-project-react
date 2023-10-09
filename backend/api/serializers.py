import base64
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)


User = get_user_model()


MIN_AMOUNT_OR_COOKING_TIME = 1
MAX_AMOUNT_OR_COOKING_TIME = 32000


class Base64ImageField(serializers.ImageField):

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class TagSerializer(serializers.ModelSerializer):

    slug = serializers.CharField(read_only=True)

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class ShowUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed',)

    def get_is_subscribed(self, obj):
        return obj.follower.filter(user=self.context['request'].user).exists()


class RecipeIngredientSerializer(serializers.ModelSerializer):

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(),
                                            source='ingredient.id')
    name = serializers.CharField(
        read_only=True,
        source='ingredient.name'
    )
    measurement_unit = serializers.CharField(
        read_only=True,
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField(
        min_value=MIN_AMOUNT_OR_COOKING_TIME,
        max_value=MAX_AMOUNT_OR_COOKING_TIME,
        error_messages={
            'min_value': f'Количество должно быть не менее '
            f'{MIN_AMOUNT_OR_COOKING_TIME}',
            'max_value': f'Количество не должно превышать '
            f'{MAX_AMOUNT_OR_COOKING_TIME}',
        }
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount', 'name', 'measurement_unit',)


class ShowingRecipeSerializer(serializers.ModelSerializer):
    author = ShowUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipe_recipe_ingredients')
    image = Base64ImageField(required=False, allow_null=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name', 'image',
            'cooking_time',
            'text',
            'is_favorited',
            'is_in_shopping_cart',)

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return (not user.is_anonymous
                and obj.favored_by.filter(user=user).exists())

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return (not user.is_anonymous
                and obj.carts.filter(user=user).exists())


class RecipePostSerializer(ShowingRecipeSerializer):

    ingredients = RecipeIngredientSerializer(
        source='recipe_recipe_ingredients',
        many=True,)
    image = Base64ImageField(required=False, allow_null=True)
    author = ShowUserSerializer(read_only=True, required=False)
    tags = serializers.PrimaryKeyRelatedField(many=True,
                                              queryset=Tag.objects.all())
    cooking_time = serializers.IntegerField(
        min_value=MIN_AMOUNT_OR_COOKING_TIME,
        max_value=MAX_AMOUNT_OR_COOKING_TIME,
        error_messages={
            'min_value': f'Время приготовления должно быть не менее '
            f'{MIN_AMOUNT_OR_COOKING_TIME}',
            'max_value': f'Время приготовления не должно превышать '
            f'{MAX_AMOUNT_OR_COOKING_TIME}',
        }
    )

    class Meta:
        model = Recipe
        fields = '__all__'
        read_only_fields = ('author',)

    def process_ingredients(self, recipe, ingredients):
        ingredients_list = []
        for ingredient in ingredients:
            ingredient_id = ingredient['ingredient']['id']
            current_amount = ingredient.get('amount')
            ingredients_list.append(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=ingredient_id,
                    amount=current_amount
                )
            )
        return ingredients_list

    def create(self, validated_data):
        author = self.context.get('request').user
        ingredients = validated_data.pop('recipe_recipe_ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.save()
        recipe.tags.set(tags)
        ingredients_list = self.process_ingredients(recipe, ingredients)
        RecipeIngredient.objects.bulk_create(ingredients_list)
        return recipe

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('recipe_recipe_ingredients')
        tags = validated_data.pop('tags')
        instance.tags.set(tags)
        instance.recipe_recipe_ingredients.all().delete()
        ingredients_list = self.process_ingredients(instance, ingredients)
        RecipeIngredient.objects.bulk_create(ingredients_list)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        return ShowingRecipeSerializer(
            instance,
            context={'request': self.context.get('request')}).data


class FavouriteSerializer(serializers.ModelSerializer):
    image = Base64ImageField(read_only=True)
    name = serializers.ReadOnlyField()
    cooking_time = serializers.ReadOnlyField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time',)
        read_only_fields = ('__all__',)


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe',)


class CreateUserSerializer(UserCreateSerializer):
    email = serializers.EmailField(max_length=254)
    username = serializers.CharField(max_length=150)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'password',)


class FavoriteShopingCartSubsrRecipeSerializer(serializers.ModelSerializer):

    image = Base64ImageField(read_only=True)
    name = serializers.ReadOnlyField()
    cooking_time = serializers.ReadOnlyField()

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return (not user.is_anonymous
                and obj.favored_by.filter(user=user).exists())

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return (not user.is_anonymous
                and obj.carts.filter(user=user).exists())


class UserSubscribeSerializer(ShowUserSerializer):
    first_name = serializers.ReadOnlyField()
    last_name = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField()
    username = serializers.ReadOnlyField()
    is_subscribed = serializers.SerializerMethodField()
    recipes = FavouriteSerializer(many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id',
                  'username', 'first_name',
                  'last_name', 'is_subscribed',
                  'recipes', 'recipes_count',)

    def validate(self, data):
        data = super().validate(data)
        request = self.context['request'].user
        author = self.instance
        user = request.user if request else None
        if user == author:
            raise serializers.ValidationError('Нельзя подписаться на себя.')
        if user and user.follower.filter(author=author).exists():
            raise serializers.ValidationError('Вы уже подписаны.')
        return data

    def get_is_subscribed(self, obj):
        request = self.context['request'].user
        if request and not request.user.is_anonymous:
            return obj.follower.filter(user=request.user).exists()
        return False

    def get_recipes_count(self, obj: User) -> int:
        return obj.recipes.count()


class UserPasswordResetSerializer(serializers.Serializer):

    current_password = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.instance.check_password(value):
            raise serializers.ValidationError('Неправильный пароль.')
        return value

    def save(self):
        self.instance.set_password(self.validated_data['new_password'])
        self.instance.save()
