from email.policy import default
from locale import currency
from django.db import models
import time
from datetime import datetime


def uploada_path_handler(instance, filename):
    return f'models/{instance.currency_id}/{str(instance.interval_id)}Min/{str(instance.currency_id)}_{str(instance.interval_id)}_{str(time.time())}_{filename}'


class ReportStatus(models.Model):
    # request_id = models.CharField(max_length=200, default="adoreta")
    status = models.IntegerField()
    comment = models.TextField(max_length=200)
    user_id = models.CharField(max_length=200)
    date_time = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.id)


class Currency(models.Model):
    currency_name = models.CharField(max_length=50)
    description = models.TextField(max_length=500)

    def __str__(self) -> str:
        return self.currency_name


class Interval(models.Model):
    minutes = models.IntegerField()
    description = models.TextField()

    def __str__(self) -> str:
        return str(self.minutes)


class ForexModel(models.Model):
    currency_id = models.ForeignKey(Currency, on_delete=models.CASCADE)
    interval_id = models.ForeignKey(Interval, on_delete=models.CASCADE)
    model_high = models.FileField(upload_to=uploada_path_handler)
    model_low = models.FileField(upload_to=uploada_path_handler)
    version = models.CharField(max_length=50)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    date_time = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.description


class ReportHistoryPrediction(models.Model):
    report_status = models.ForeignKey(ReportStatus, on_delete=models.CASCADE)
    # request_id = models.CharField(max_length=200, default="adoreta")
    currency_id = models.ForeignKey(Currency, on_delete=models.CASCADE)
    interval_id = models.ForeignKey(Interval, on_delete=models.CASCADE)
    prediction_high = models.FloatField()
    prediction_low = models.FloatField()
    target_datetime = models.DateTimeField()
    predicted_hit_high = models.DateTimeField(null=True)
    predicted_hit_low = models.DateTimeField(null=True)
    current_date_time = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.id)


class Report(models.Model):
    report_status = models.ForeignKey(ReportStatus, on_delete=models.CASCADE)
    currency_id = models.ForeignKey(Currency, on_delete=models.CASCADE)
    interval_id = models.ForeignKey(Interval, on_delete=models.CASCADE)
    from_date = models.DateTimeField(null=True)
    to_date = models.DateTimeField(null=True)
    percentage = models.FloatField(default=0.0)
    report_date_time = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.percentage)
