from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import filters, status, viewsets

from api.filters import RecipeFilter
from api.pagination import CustomPaginator
from api.serializers import (CreateUserSerializer,
                             FavoriteShopingCartSubsrRecipeSerializer,
                             FavouriteSerializer, IngredientSerializer,
                             RecipePostSerializer, ShowingRecipeSerializer,
                             ShowUserSerializer, TagSerializer,
                             UserPasswordResetSerializer,
                             UserSubscribeSerializer)
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Follow


User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    pagination_class = CustomPaginator
    http_method_names = ['get', 'post', 'delete']

    def get_serializer_class(self):
        if self.action in ['subscriptions', 'subscribe']:
            return UserSubscribeSerializer
        if self.request.method == 'GET':
            return ShowUserSerializer
        if self.request.method == 'POST':
            return CreateUserSerializer

    def get_permissions(self):
        if self.action == 'retrieve':
            self.permission_classes = [IsAuthenticated, ]
        return super(self.__class__, self).get_permissions()

    @action(detail=False, methods=['get'],
            pagination_class=None,
            permission_classes=(IsAuthenticated,))
    def me_users(self, request):
        serializer = ShowUserSerializer(request.user)
        return Response(serializer.data,
                        status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'],
            permission_classes=(IsAuthenticated,))
    def reset_password(self, request):
        serializer = UserPasswordResetSerializer(
            request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Пароль изменен'},
                        status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=(IsAuthenticated,),
            pagination_class=CustomPaginator)
    def subscriptions(self, request):
        queryset = User.objects.filter(following__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = UserSubscribeSerializer(page, many=True,
                                             context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, **kwargs):
        author = get_object_or_404(User, id=kwargs['id'])
        serializer = UserSubscribeSerializer(
            author, data=request.data, context={'request': request})
        if request.method == 'POST':
            serializer.is_valid(raise_exception=True)
            user = request.user
            if author.following.filter(user=user).exists():
                return Response({'detail': 'Вы уже подписаны'},
                                status=status.HTTP_400_BAD_REQUEST)
            Follow.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            user = request.user
            author.following.filter(user=user).delete()
            return Response({'detail': 'Вы отписались'},
                            status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    pagination_class = None


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    lookup_field = 'name__istartswith'
    pagination_class = None

    def get_queryset(self):
        queryset = self.queryset
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPaginator
    filterset_class = RecipeFilter
    filter_backends = (DjangoFilterBackend, )
    ordering = ['id']

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ShowingRecipeSerializer
        if self.action in ['favorite_recipe', 'shopping_cart', ]:
            return FavoriteShopingCartSubsrRecipeSerializer

        return RecipePostSerializer

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        serializer = FavouriteSerializer(recipe, context={'request': request})
        if request.method == 'POST':
            if request.user.favorite_recipes.filter(recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже добавлен в избранное'},
                                status=status.HTTP_400_BAD_REQUEST)
            Favorite.objects.create(user=request.user, recipe=recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not request.user.favorite_recipes.filter(recipe=recipe).exists():
            return Response({'errors': 'Рецепта нет в избранном'},
                            status=status.HTTP_400_BAD_REQUEST)
        favorite = get_object_or_404(Favorite, user=request.user,
                                     recipe=recipe)
        favorite.delete()
        return Response({'detail': 'Рецепт удален из избранного'},
                        status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,),
            pagination_class=None)
    def shopping_cart(self, request, **kwargs):
        recipe = self.get_object()
        user = request.user

        if request.method == 'POST':
            if user.cart.filter(recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в списке покупок'},
                                status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = FavoriteShopingCartSubsrRecipeSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            cart_item = user.cart.filter(recipe=recipe).first()
            if not cart_item:
                return Response({'errors': 'Рецепта нет в списке покупок'},
                                status=status.HTTP_400_BAD_REQUEST)
            cart_item.delete()
            return Response({'detail': 'Рецепт удален из списка покупок'},
                            status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated, ]
    )
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart_items = ShoppingCart.objects.filter(user=user)
        recipes = [item.recipe for item in shopping_cart_items]
        ingredients = RecipeIngredient.objects.filter(recipe__in=recipes)
        ingredient_data = ingredients.values(
            recipe_name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')
        ).annotate(
            amount=Sum('amount')
        )
        file_name = 'shopping_cart.txt'
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        for ingredient in ingredient_data:
            response.write(
                f"{ingredient['recipe_name']} - {ingredient['amount']}"
                f" {ingredient['measurement_unit']}\n"
            )
        return response
