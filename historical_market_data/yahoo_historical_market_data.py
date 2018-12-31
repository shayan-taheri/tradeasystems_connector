from tradeasystems_connector.conf.log_settings import logger
from tradeasystems_connector.conf.region_settings import timezone_setting
from tradeasystems_connector.historical_market_data.historical_market_data import HistoricalMarketData
from tradeasystems_connector.model.asset_type import AssetType
from tradeasystems_connector.model.bar import Bar
from tradeasystems_connector.model.period import Period


class YahooHistoricalMarketData(HistoricalMarketData):
    period_dict = \
        {
            Period.day: 'day',
            Period.minute: 'minute',
            Period.hour: 'hour'
        }

    columns_historical_dict = \
        {
            Bar.close: 'Adj Close',
            Bar.open: 'Open',
            Bar.high: 'High',
            Bar.low: 'Low',
            Bar.time: 'Date',
            Bar.volume: 'Volume'
        }

    def __init__(self, user_settings):
        HistoricalMarketData.__init__(self, user_settings);
        pass

    def formatTime(self, timeColumn):
        import pandas as pd
        # The price comes from the daily info -
        #  so it would be the price at the end of the day GMT based on the requested TS

        # http://pvlib-python.readthedocs.io/en/latest/timetimezones.html
        originTZ = 'Etc/GMT'

        datetimeSeries = pd.to_datetime(timeColumn)
        return pd.DatetimeIndex(pd.to_datetime(datetimeSeries, unit='ms')).tz_localize(originTZ).tz_convert(
            timezone_setting)

    def formatHistorical(self, input_df):
        import pandas as pd

        output = pd.DataFrame(0, columns=Bar.columns, index=range(len(input_df)))
        input_df.reset_index(inplace=True)
        for column in output.columns:
            if column == Bar.time:
                timeProcessed = self.formatTime(input_df[self.columns_historical_dict[column]])
                output[column] = timeProcessed
            else:
                output[column] = input_df[self.columns_historical_dict[column]]

        output.set_index(Bar.index, inplace=True)

        return output

    # day unlimited
    # minute limited to 7 days!
    def download(self, instrument, period, number_of_periods, fromDate, toDate=None):
        import datetime
        logger.debug("Downloading %s yahoo" % (instrument.symbol))

        import fix_yahoo_finance as yf
        yf.pdr_override()  # <== that's all it takes :-)

        if period != Period.day:
            logger.error("Yahoo can only download daily! not %s" % period)
            return None
        dateFormat = "%Y-%m-%d"
        if toDate is None:
            toDate = datetime.datetime.today()
        # download dataframe
        try:
            if instrument.asset_type == AssetType.index and not instrument.symbol.upper().startswith('^'):
                symbolToDownload = '^' + instrument.symbol.upper()
            else:
                symbolToDownload = instrument.symbol.upper()

            data_downloaded = yf.download(symbolToDownload, start=fromDate.strftime(dateFormat),
                                          end=toDate.strftime(dateFormat))
            # data_downloaded = pdr.get_data_yahoo(instrument.symbol, start=fromDate.strftime(dateFormat), end=toDate.strftime(dateFormat))
        except Exception as e:
            logger.error("Cant download from yahoo %s %s  => return None   %s" % (instrument.symbol, period, e))
            return None

        outputComplete = self.formatHistorical(data_downloaded)
        outputComplete = self.setTimeCorrect(outputComplete, period=period, instrument=instrument)
        return outputComplete
