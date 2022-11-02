from pyexpat import model
from rest_framework import serializers
from .models import *


class CurrencySerializer(serializers.ModelSerializer):

    class Meta:
        model = Currency
        fields = ['id', 'currency_name', 'description']


class IntervalSerializer(serializers.ModelSerializer):

    class Meta:
        model = Interval
        fields = ['id', 'minutes', 'description']