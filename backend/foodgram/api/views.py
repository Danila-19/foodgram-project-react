from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.models import Follow

from api.pagination import CustomPaginator
from api.serializers import (CreateUserSerializer,
                             FavoriteShopingCartSubsrRecipeSerializer,
                             IngredientSerializer, RecipePostSerializer,
                             ShowingRecipeSerializer, ShowUserSerializer,
                             TagSerializer, UserPasswordResetSerializer,
                             UserSubscribeSerializer)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    pagination_class = CustomPaginator
    http_method_names = ['get', 'post', 'delete']

    def get_serializer_class(self):

        if self.action in ['subscriptions', 'subscribe']:
            return UserSubscribeSerializer
        elif self.request.method == 'GET':
            return ShowUserSerializer
        elif self.request.method == 'POST':
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

        if request.method == 'POST':
            serializer = UserSubscribeSerializer(
                author, data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            if author == request.user:
                return Response({'detail': 'Нельзя.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if Follow.objects.filter(user=request.user,
                                     author=author).exists():
                return Response({'detail': 'Вы уже подписаны'},
                                status=status.HTTP_400_BAD_REQUEST)
            Follow.objects.create(user=request.user, author=author)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)

        try:
            follow = Follow.objects.get(user=request.user, author=author)
        except Follow.DoesNotExist:
            return Response({'detail': 'Вы не подписаны'},
                            status=status.HTTP_400_BAD_REQUEST)
        follow.delete()
        return Response({'detail': 'Вы отписались'},
                        status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()


class IngredientViewSet(viewsets.ModelViewSet):
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPaginator

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ShowingRecipeSerializer
        elif self.action in ['favorite_recipe', 'shopping_cart', ]:
            return FavoriteShopingCartSubsrRecipeSerializer

        return RecipePostSerializer

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def favorite_recipe(self, request, **kwargs):
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        serializer = FavoriteShopingCartSubsrRecipeSerializer(
            recipe, context={"request": request})
        if request.method == 'POST':
            if Favorite.objects.filter(user=request.user,
                                       recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в избранном'},
                                status=status.HTTP_400_BAD_REQUEST)
            Favorite.objects.create(user=request.user, recipe=recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            if not Favorite.objects.filter(user=request.user,
                                           recipe=recipe).exists():
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
        recipe = get_object_or_404(Recipe, id=kwargs['pk'])
        if request.method == 'POST':
            serializer = FavoriteShopingCartSubsrRecipeSerializer(
                recipe, data=request.data,
                context={"request": request})
            serializer.is_valid()
            if ShoppingCart.objects.filter(user=request.user,
                                           recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not ShoppingCart.objects.filter(user=request.user,
                                               recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепта нет в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST)
            get_object_or_404(ShoppingCart, user=request.user,
                              recipe=recipe).delete()
            return Response(
                {'detail': 'Рецепт удален из списка покупок'},
                status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated, ]
    )
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart = Recipe.objects.filter(cart__user=user)
        ingredients = shopping_cart.values(
            recipe_name=F('ingredients__name'),
            measurement_unit=F('ingredients__measurement_unit')
                            ).annotate(
            amount=Sum('recipe_ingredients__amount')
                            )
        file_name = 'shopping_cart.txt'
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        for ingredient in ingredients:
            response.write(
                f"{ingredient['recipe_name']} - {ingredient['amount']}"
                f" {ingredient['measurement_unit']}\n")
        return response
