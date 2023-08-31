from django.shortcuts import HttpResponse
from djoser.views import UserViewSet
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet
from recipes.models import Tag, Ingredient
from .serializers import (TagSerializer, IngredientSerializer,
                          RecipeSerializer)


def index(request):
    return HttpResponse('index')


class CustomUserViewSet(UserViewSet):
    pass


class TagViewSet(ModelViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()


class IngredientViewSet(ModelViewSet):
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()


class RecipeViewSet(ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = IsAuthenticatedOrReadOnly
