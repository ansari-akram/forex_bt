from asyncio.windows_events import NULL
import os
from posixpath import sep
from sqlite3 import Timestamp
import time
import pytz
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from silence_tensorflow import silence_tensorflow
from tensorflow.keras.models import load_model
from sklearn.preprocessing import StandardScaler
from urllib.parse import quote
from .models import *
import csv
from dateutil import tz
from .models import *
from .past_prediction import get_rsi, moving_avg, get_data_mt5, get_forecast_df, get_data_mt5_resample_1Min
import os

silence_tensorflow()
N_PAST = 48
N_FUTURE = 1
BASE_CSV_DIR = 'live_data_csv'
forecast_period_dates = ""
BASE_DIR = os.getcwd()


def get_next_interval_high_low_values(_currency_name, _interval, _from_date, _to_date, _target_time):
    print("NEXT DATA VALUES", _currency_name,
          _interval, _from_date, _to_date, _target_time)
    next_df = get_data_mt5_resample_1Min(
        _currency_name, _interval, _from_date, _to_date)

    # print(next_df)
    # print(next_df.size)
    if next_df is not None and len(next_df) != 0:
        # print(_target_time.tz_localize(
        #     'Asia/Kolkata').isoformat(), type(_target_time))
        timestamp = pd.Timestamp(_from_date).tz_localize(None)

        # print(timestamp, type(timestamp))
        # print(_target_time, type(_target_time))
        # print(next_df.loc[(next_df['time'] >= timestamp) & (next_df['time'] <= _target_time)])
        _df = next_df.loc[(next_df['time'] >= timestamp) &
                          (next_df['time'] <= _target_time)]

        # print(_df.size)

        # _row_start_index = next_df.loc[next_df['time'] == timestamp].index.values.astype(int)[0]
        # _row_index = next_df.loc[next_df['time'] == _target_time].index.values.astype(int)[
        #     0]

        # print("START INDEX", _row_start_index)
        # print(next_df.tail(1))
        _high_col = _df.loc[:, ["high", "time"]]
        _low_col = _df.loc[:, ["low", "time"]]
        # print(_high_col.size, _low_col.size)
        # print("HIGH", _row.iloc[0]["high"])
        # todo : check highest value from time interval to next time interval which will be less than or greater than predicted high value

        # print("LOW", _row.iloc[0]["low"])
        # print(next_df.loc['time'].tz_localize(
        #     'Asia/Kolkata').isoformat(), _target_time)
        # print(next_df.loc[next_df['time'].tz_localize(
        # 'Asia/Kolkata').isoformat() == _target_time])
        # print("TARGET TIME COMPARE", next_df.iloc[-1]["time"].tz_localize('Asia/Kolkata').isoformat(
        # ) == _target_time, next_df.iloc[-1]["time"].tz_localize('Asia/Kolkata').isoformat(), _target_time)
        return _high_col, _low_col
    else:
        0, 0


def past_predict_by_model(_user_id, _request_id, _from_date, _to_date, _currency_id, _interval_id, _model_id, _rs):
    sc = StandardScaler()
    cols = ['high', 'low', 'RSI_HLCC/4', 'MA_Slow_HLCC/4', 'MA_Fast_HLCC/4']
    # _interval_list = [int(i) for i in _interval_list]
    # C:\Users\ansar\Downloads\FOREX\forex_api\models\AUDUSD\30Min\AUDUSD_30_1659594602.1204534_high.h5
    # C:\Users\ansar\Downloads\FOREX\forex_api\models\AUDUSD\30Min\AUDUSD_30_1659594602.1285079_low.h5
    print('\nHIGH MODEL', os.path.join(
        BASE_DIR, _model_id.model_high.__str__()))
    print('LOW MODEL', os.path.join(BASE_DIR, _model_id.model_low.__str__()))

    _model_high = load_model(os.path.join(
        BASE_DIR, _model_id.model_high.__str__()))
    _model_low = load_model(os.path.join(
        BASE_DIR, _model_id.model_low.__str__()))

    all_loaded_models = [_model_high, _model_low]
    # print("ALL LOADED MODELS", all_loaded_models)

    _from_date = _from_date.astimezone(tz.gettz('Asia/Kolkata'))
    _to_date = _to_date.astimezone(tz.gettz('Asia/Kolkata'))

    delta = _to_date - _from_date
    error_bool = True
    error_msg = "result saved"
    interval_int = int(_interval_id.__str__())

    try:
        for d in range(delta.days):
            minute = 0
            for m in range(1440 // interval_int):
                minute += interval_int
                print('DATE TIME', _from_date +
                      timedelta(days=d, minutes=minute), _from_date, _from_date + timedelta(days=d, minutes=minute), interval_int)
                og_df = get_data_mt5(
                    _currency_id, interval_int, _from_date, _from_date + timedelta(days=d, minutes=minute))

                high_model = all_loaded_models[0]
                low_model = all_loaded_models[1]
                # print(
                #     "#############################################################################")
                # print(og_df.head(2))
                # print(og_df.tail(2))
                # print(
                #     "#############################################################################")
                # print(high_model, low_model)

                if og_df is not None and len(og_df) != 0:
                    train_dates = og_df['time']
                    # print('train_dates', train_dates.values[-1], interval_int)
                    from_date = pd.to_datetime(
                        train_dates.values[-1]) + timedelta(minutes=interval_int)
                    # print("single from date", from_date,
                    #       train_dates.values[-1], interval_int)
                    forecast_period_dates = pd.date_range(
                        from_date, periods=N_FUTURE, freq=str(f'{interval_int}Min')).tolist()
                    # print("forecast period dates", forecast_period_dates)

                    train_set = og_df[cols].astype(float)
                    scaled_data = sc.fit_transform(train_set)
                    x_train = []
                    # print(N_PAST, len(scaled_data), N_FUTURE, x_train)
                    for x in range(N_PAST, len(scaled_data) - N_FUTURE + 1):
                        x_train.append(
                            scaled_data[x + 1 - N_PAST:x + 1, 0:scaled_data.shape[1]])

                    x_train = np.array(x_train)
                    # print('after', x_train.shape)

                    high_df_forecast = get_forecast_df(
                        high_model, x_train, 0, 'high', train_set, sc, forecast_period_dates)
                    low_df_forecast = get_forecast_df(
                        low_model, x_train, 1, 'low', train_set, sc, forecast_period_dates)

                    # print(high_df_forecast)
                    # print(low_df_forecast)
                    # print(high_df_forecast.empty, low_df_forecast.empty)

                    if not high_df_forecast.empty and not low_df_forecast.empty:
                        # if og_df['time'].values[-1] <= high_df_forecast['time'].values[-1]:
                        current_time = pd.to_datetime(
                            og_df['time'].values[-1]).tz_localize('Asia/Kolkata').isoformat()
                        # current_time = pd.to_datetime(
                        #     og_df['time'].values[-1])
                        high_value = np.float32(
                            og_df['high'].values[-1]).item()
                        low_value = np.float32(
                            og_df['low'].values[-1]).item()
                        predicted_high_value = np.float32(
                            high_df_forecast['high'].values[-1]).item()
                        predicted_low_value = np.float32(
                            low_df_forecast['low'].values[-1]).item()
                        target_time = pd.to_datetime(
                            high_df_forecast['time'].values[-1])

                        # print(f'{_from_date + timedelta(hours=h, minutes=minute - i)} {high_value} {low_value}
                        # {predicted_high_value} {predicted_low_value} {target_time} {i}Min') writer.writerow([
                        # _from_date + timedelta(hours=h, minutes=i - i), high_value, low_value,
                        # predicted_high_value, predicted_low_value, target_time, str(i)+"Min"])
                        print(
                            f'PREDICTION DATA VALUES | {current_time} | {high_value} {low_value} | {predicted_high_value} {predicted_low_value} | {target_time} {interval_int}Min')

                        ##########################################################################################################
                        # todo: get current high, low for next interval and compare with predicted high, low value               #
                        ##########################################################################################################
                        # print("CURRENT DATA VALUES", _currency_id, interval_int,
                        #       _from_date, _to_date,  d, minute, type(current_time))
                        _next_date = _from_date + \
                            timedelta(days=d, minutes=minute)
                        _from_date_with_interval = _from_date + \
                            timedelta(days=d, minutes=minute - interval_int)

                        # print(
                        #     f"VARS {interval_int} | {_from_date} | {minute} | {_next_date} | {target_time} | {_from_date_with_interval}")
                        next_high, next_low = get_next_interval_high_low_values(
                            _currency_id, interval_int, _from_date_with_interval, _next_date, target_time)

                        # print(next_high)
                        # print(next_low)

                        hit_high = None
                        hit_low = None

                        if not next_high.empty and not next_low.empty:
                            # print(next_high.sort_values('high').tail(3))
                            # print(next_low.sort_values('low').tail(3))
                            high_row = next_high.sort_values('high').values[-1]
                            low_row = next_low.sort_values('low').values[-1]

                            print("HIGH ROWS", high_row, low_row)
                            # print(high_row[0], low_row[0], high_row[1], low_row[1])

                            if high_row[0] >= predicted_high_value:
                                hit_high = high_row[1].tz_localize('Asia/Kolkata').isoformat()

                            if low_row[0] >= predicted_low_value:
                                hit_low = low_row[1].tz_localize('Asia/Kolkata').isoformat()

                        print("HIT", hit_high, hit_low)

                        # print(
                        #     f'COMPARE {current_time} | {high_value}, {predicted_high_value}, {next_high} | {low_value}, {predicted_low_value}, {next_low}')

                        ReportHistoryPrediction.objects.create(report_status=_rs, currency_id=_currency_id,
                                                               interval_id=_interval_id,
                                                               prediction_high=predicted_high_value,
                                                               prediction_low=predicted_low_value,
                                                               predicted_hit_high=hit_high,
                                                               predicted_hit_low=hit_low,
                                                               target_datetime=target_time.tz_localize('Asia/Kolkata').isoformat())
                        print()

    except Exception as e:
        error_bool = False
        error_msg = e
        print("[ERROR]", e)
        print("[ERROR]", e.args)
        _rs.status = '1'
        _rs.comment = f'{e}'
        # ReportStatus.objects.filter(request_id=_request_id).update(
        #     status='1', comment=f'{e}')

    print("FINISHED")
    return error_bool, error_msg
