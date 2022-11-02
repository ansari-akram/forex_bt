from django.contrib import admin
from .models import *


class ReportStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'comment', 'user_id', 'date_time')


class ReportHistoryPredictionAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_status', 'currency_id', 'interval_id', 'prediction_high', 'prediction_low', 'target_datetime',
                    'predicted_hit_high', 'predicted_hit_low', 'current_date_time')


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('id', 'currency_name', 'description')


class IntervalAdmin(admin.ModelAdmin):
    list_display = ('id', 'minutes', 'description')


class ForexModelAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'model_high', 'model_low', 'currency_id', 'interval_id', 'version', 'description', 'is_active', 'date_time')


class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'report_status', 'currency_id', 'interval_id', 'from_date', 'to_date', 'percentage', 'report_date_time')


admin.site.register(ReportStatus, ReportStatusAdmin)
admin.site.register(ReportHistoryPrediction, ReportHistoryPredictionAdmin)
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Interval, IntervalAdmin)
admin.site.register(ForexModel, ForexModelAdmin)
admin.site.register(Report, ReportAdmin)
