import os
from posixpath import sep
import time
import pytz
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone
from silence_tensorflow import silence_tensorflow
from tensorflow.keras.models import load_model
from sklearn.preprocessing import StandardScaler
from urllib.parse import quote
from .models import *
import csv
from dateutil import tz
from .models import *

silence_tensorflow()
N_PAST = 48
N_FUTURE = 1
LOCAL_HOUR_TO_ADD = 5
LOCAL_MIN_TO_ADD = 30
BASE_MODEL_DIR = f'forex{os.sep}trained_models'
BASE_CSV_DIR = 'live_data_csv'
forecast_period_dates = ""


def get_rsi(file, value, n):
    """
    calculates -> RSI value
    takes argument -> dataframe, column name, period value
    returns dataframe by adding column : 'RSI_' + column name
    """
    delta = file[value].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(span=n, adjust=False).mean()
    ema_down = down.ewm(span=n, adjust=False).mean()
    rs = ema_up / ema_down
    file['RSI_' + value] = 100 - (100 / (1 + rs))

    return file


def moving_avg(ultratech_df, value, fast_p, slow_p):
    """
    calculates -> slow moving average, fast moving average
    takes argument -> dataframe, column name, slow period, fast period
    returns dataframe by adding columns -> 'MA_Slow_HLCC/4',  'SMA_period', MA_Fast_HLCC/4', 'FMA_period'
    """
    ultratech_df['MA_Slow_HLCC/4'] = ultratech_df[value].rolling(
        window=17, min_periods=1).mean()
    ultratech_df['SMA_period'] = slow_p
    ultratech_df['MA_Fast_HLCC/4'] = ultratech_df[value].rolling(
        window=7, min_periods=1).mean()
    ultratech_df['FMA_period'] = fast_p

    return ultratech_df


def get_data_mt5_resample_1Min(currency_name, interval, from_date_time, to_date_time):
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return None
    try:
        utc_from = from_date_time - timedelta(days=1)
        utc_to = to_date_time + timedelta(days=1)

        # print("GET DATA MT5", utc_from, utc_to, currency_name, interval, type(currency_name.__str__()), type(interval), type(utc_from), type(utc_to))

        ticks = mt5.copy_ticks_range(
            currency_name.__str__(), utc_from, utc_to, mt5.COPY_TICKS_ALL)
        
        # print('ticks', ticks)
        ticks_frame = pd.DataFrame(ticks)
        # print('ticks_frame', ticks_frame)
        ticks_frame['time'] = pd.to_datetime(ticks_frame['time'], unit='s')
        ticks_frame = ticks_frame.set_index(ticks_frame['time'])

        # data_ask = ticks_frame['ask'].resample("1Min").ohlc()
        # data_bid = ticks_frame['bid'].resample("1Min").ohlc()
        data_ask = ticks_frame['ask'].resample(str(1)+"Min").ohlc()
        data_bid = ticks_frame['bid'].resample(str(1)+"Min").ohlc()

        data = pd.DataFrame()
        data['open'] = (data_ask['open'] + data_bid['open']) / 2
        data['high'] = (data_ask['high'] + data_bid['high']) / 2
        data['low'] = (data_ask['low'] + data_bid['low']) / 2
        data['close'] = (data_ask['close'] + data_bid['close']) / 2
        data = data.reset_index()

        # data = data.reset_index()
        data['HLCC/4'] = (data['high'] + data['low'] +
                          data['close'] + data['close']) / 4
        data = get_rsi(data, 'HLCC/4', 14)
        data = moving_avg(data, 'HLCC/4', 17, 7)
        data = data.dropna()
        # data = data.tail(5000)
        # print(data.tail())
        # data.to_csv('data.csv')
        mt5.shutdown()

        return data
    except Exception as e:
        print("[ERROR]", e)
        return None


def get_data_mt5(currency_name, interval, from_date_time, to_date_time):
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return None
    try:
        print(from_date_time, to_date_time)
        utc_from = from_date_time - timedelta(days=15)
        utc_to = to_date_time + timedelta(hours=LOCAL_HOUR_TO_ADD, minutes=LOCAL_MIN_TO_ADD)

        print("GET DATA MT5", utc_from, utc_to, currency_name, interval, type(currency_name.__str__()), type(interval), type(utc_from), type(utc_to))

        ticks = mt5.copy_ticks_range(
            currency_name.__str__(), utc_from, utc_to, mt5.COPY_TICKS_ALL)
        
        # print('ticks', ticks)
        ticks_frame = pd.DataFrame(ticks)
        # print('ticks_frame', ticks_frame)
        ticks_frame['time'] = pd.to_datetime(ticks_frame['time'], unit='s')
        ticks_frame = ticks_frame.set_index(ticks_frame['time'])

        # data_ask = ticks_frame['ask'].resample("1Min").ohlc()
        # data_bid = ticks_frame['bid'].resample("1Min").ohlc()
        data_ask = ticks_frame['ask'].resample(str(interval)+"Min").ohlc()
        data_bid = ticks_frame['bid'].resample(str(interval)+"Min").ohlc()

        data = pd.DataFrame()
        data['open'] = (data_ask['open'] + data_bid['open']) / 2
        data['high'] = (data_ask['high'] + data_bid['high']) / 2
        data['low'] = (data_ask['low'] + data_bid['low']) / 2
        data['close'] = (data_ask['close'] + data_bid['close']) / 2
        data = data.reset_index()

        # data = data.reset_index()
        data['HLCC/4'] = (data['high'] + data['low'] +
                          data['close'] + data['close']) / 4
        data = get_rsi(data, 'HLCC/4', 14)
        data = moving_avg(data, 'HLCC/4', 17, 7)
        data = data.dropna()
        # data = data.tail(5000)
        # print(data.tail(3))
        # data.to_csv('data.csv')
        mt5.shutdown()

        return data
    except Exception as e:
        print("[ERROR]", e)
        return None


def get_forecast_df(model, x_train, col_ind, col_name, train_set, sc, forecast_period_dates):
    """
    returns next prediction in a dataframe
    """

    # global forecast_period_dates
    forecast = model.predict(x_train[-N_FUTURE:])  # forecast
    forecast_copies = np.repeat(forecast, train_set.shape[1], axis=-1)
    y_pred_future = sc.inverse_transform(forecast_copies)[:, col_ind]
    forecast_dates = []
    for time_i in forecast_period_dates:
        forecast_dates.append(time_i)

    df_forecast = pd.DataFrame(
        {'time': np.array(forecast_dates), col_name: y_pred_future})
    df_forecast['time'] = pd.to_datetime(df_forecast['time'])

    return df_forecast


def past_predict(_user_id, _request_id, _from_date, _to_date, _currency_id, _interval_list, _model_id):
    sc = StandardScaler()
    cols = ['high', 'low', 'RSI_HLCC/4', 'MA_Slow_HLCC/4', 'MA_Fast_HLCC/4']
    _interval_list = [int(i) for i in _interval_list]
    print('interval list', _interval_list)
    all_loaded_models = []

    for i in _interval_list:
        for root, dirs, files in os.walk(BASE_MODEL_DIR + os.sep + _currency_id):
            # for d in dirs:
            try:
                if i == int(root.split(os.sep)[-1].split("Min")[0]):
                    _tmp = []
                    for _d in dirs:
                        if _d == "high_model":
                            model_path = f"{root}{os.sep}{_d}{os.sep}high.h5"
                        else:
                            model_path = f"{root}{os.sep}{_d}{os.sep}low.h5"

                        _model = load_model(model_path, compile=False)
                        _tmp.append(_model)

                    _tmp.append(_currency_id)
                    _tmp.append(i)
                    all_loaded_models.append(_tmp)

            except Exception as e:
                pass

    print(len(all_loaded_models), _interval_list)

    # f = open('prediction.csv', 'w', newline="")
    # writer = csv.writer(f)
    # writer.writerow(['time', 'actual_high', 'actula_low', 'predicted_high',
    #                 'predicted_low', 'target_datetime', 'interval'])

    # print("FROM DATE", _from_date)
    # print("TO DATE", _to_date)
    _from_date = _from_date.astimezone(tz.gettz('Asia/Kolkata'))
    _to_date = _to_date.astimezone(tz.gettz('Asia/Kolkata'))

    # print(pytz.all_timezones)

    delta = _to_date - _from_date
    error_bool = True
    error_msg = "Success: result saved"

    try:
        for i in _interval_list:
            for d in range(delta.days):
                for h in range(24):
                    minute = 0
                    for m in range(int(60 / i)):
                        minute += i
                        # print('from date', _from_date, "to date", _to_date,
                        #       "day", d, "hour", h, "mminute", minute, m, "i", i)
                        og_df = get_data_mt5(_currency_id, i, _from_date, _from_date +
                                            timedelta(days=d, hours=h, minutes=minute), h, minute)
                        for j in all_loaded_models:
                            if int(j[-1]) == i:
                                models = j

                        # print(og_df.tail())

                        high_model = models[0]
                        low_model = models[1]

                        if og_df is not None and len(og_df) != 0:
                            train_dates = og_df['time']
                            # print('train_dates', train_dates.values[-1])
                            from_date = pd.to_datetime(
                                train_dates.values[-1]) + timedelta(minutes=i)
                            # print("single from date", from_date)
                            forecast_period_dates = pd.date_range(
                                from_date, periods=N_FUTURE, freq=str(f'{i}Min')).tolist()
                            # print("forecase period dates", forecast_period_dates)

                            train_set = og_df[cols].astype(float)
                            scaled_data = sc.fit_transform(train_set)
                            x_train = []

                            for x in range(N_PAST, len(scaled_data) - N_FUTURE + 1):
                                x_train.append(
                                    scaled_data[x + 1 - N_PAST:x + 1, 0:scaled_data.shape[1]])

                            x_train = np.array(x_train)

                            high_df_forecast = get_forecast_df(
                                high_model, x_train, 0, 'high', train_set, sc, forecast_period_dates)
                            low_df_forecast = get_forecast_df(
                                low_model, x_train, 1, 'low', train_set, sc, forecast_period_dates)

                            # print(high_df_forecast)
                            # print(low_df_forecast)

                            # print(not high_df_forecast.empty, not low_df_forecast.empty)

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
                                    high_df_forecast['time'].values[-1]).tz_localize('Asia/Kolkata').isoformat()

                                # print(f'{_from_date + timedelta(hours=h, minutes=minute - i)} {high_value} {low_value} {predicted_high_value} {predicted_low_value} {target_time} {i}Min')
                                # writer.writerow([_from_date + timedelta(hours=h, minutes=i - i), high_value, low_value, predicted_high_value, predicted_low_value, target_time, str(i)+"Min"])
                                print(
                                    f'{current_time} {high_value} {low_value} {predicted_high_value} {predicted_low_value} {target_time} {i}Min')
                                # writer.writerow(
                                #     [current_time, high_value, low_value, predicted_high_value, predicted_low_value, target_time, str(i)+"Min"])
                                ReportHistoryPrediction.objects.create(request_id=_request_id, currency=_currency_id, interval=i,
                                                                    prediction_high=predicted_high_value, prediction_low=predicted_low_value, target_datetime=target_time)
                                # print()
    
    except Exception as e:
        error_bool = False
        error_msg = e
        ReportStatus.objects.filter(request_id=_request_id).update(status='1', comment=f'{e}')

    print("FINISHED")
    return error_bool, error_msg