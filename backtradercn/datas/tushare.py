# -*- coding: utf-8 -*-
import datetime as dt
import tushare as ts
import arctic

import backtradercn.datas.utils as bdu
from backtradercn.settings import settings as conf
from backtradercn.libs.log import logging


logger = logging.getLogger(__name__)


class TsHisData(object):
    """
    Mapping one collection in 'ts_his_lib' library, download and
    maintain history data from tushare, and provide other modules with the data.
    columns: open, high, close, low, volume
    Attributes:
        coll_name(string): stock id like '000651' for gree.

    """

    def __init__(self, coll_name):
        self._lib_name = conf.CN_STOCK_LIBNAME
        # PyMongo is not fork-safe: http://api.mongodb.com/python/current/faq.html#pymongo-fork-safe
        self._store = arctic.Arctic(conf.MONGO_HOST)
        self._coll_name = coll_name
        self._library = None
        self._unused_cols = ['price_change', 'p_change', 'ma5', 'ma10', 'ma20',
                             'v_ma5', 'v_ma10', 'v_ma20', 'turnover']
        self._new_added_colls = []

    @classmethod
    def download_one_delta_data(cls, coll_name):
        """
        Download all the collections' delta data.
        :param coll_name: a stock code
        :return: None
        """
        ts_his_data = TsHisData(coll_name)
        ts_his_data.download_delta_data()

    @classmethod
    def download_all_delta_data(cls, *coll_names):
        """
        Download all the collections' delta data.
        :param coll_names: list of the collections.
        :return: None
        """
        for coll_name in coll_names:
            ts_his_data = TsHisData(coll_name)
            ts_his_data.download_delta_data()

    def download_delta_data(self):
        """
        Get yesterday's data and append it to collection,
        this method is planned to be executed at each day's 8:30am to update the data.
        1. Connect to arctic and get the library.
        2. Get today's history data from tushare and strip the unused columns.
        3. Store the data to arctic.
        :return: None
        """

        # if library is not initialized
        if self._lib_name not in self._store.list_libraries():
            self._library = self._store.initialize_library(self._lib_name)

        self._library = self._store[self._lib_name]

        self._init_coll()

        # get last day's data as delta
        end = dt.datetime.now() - dt.timedelta(days=1)
        start = end
        if self._coll_name in self._new_added_colls:
            return
        his_data = ts.get_hist_data(code=self._coll_name, start=dt.datetime.strftime(start, '%Y-%m-%d'),
                                    end=dt.datetime.strftime(end, '%Y-%m-%d'), retry_count=5)
        if len(his_data) == 0:
            logger.warning('delta data of stock %s from tushare is empty' % self._coll_name)
            return

        his_data = bdu.Utils.strip_unused_cols(his_data, *self._unused_cols)

        logger.debug(f'stock code: {self._coll_name}')
        self._library.append(self._coll_name, his_data)

    def get_data(self):
        """
        Get all the data of one collection.
        :return: data(DataFrame)
        """
        self._library = self._store[self._lib_name]

        data = self._library.read(self._coll_name).data
        # parse the date
        data.index = data.index.map(bdu.Utils.parse_date)

        return data

    def _init_coll(self):
        """
        Get all the history data when initiate the library.
        1. Connect to arctic and create the library.
        2. Get all the history data from tushare and strip the unused columns.
        3. Store the data to arctic.
        :return: None
        """

        # if collection is not initialized
        if self._coll_name not in self._library.list_symbols():
            self._new_added_colls.append(self._coll_name)
            his_data = ts.get_hist_data(code=self._coll_name, retry_count=5).sort_index()
            if len(his_data) == 0:
                logger.warning('data of stock %s from tushare when initiation is empty' % self._coll_name)
                return

            his_data = bdu.Utils.strip_unused_cols(his_data, *self._unused_cols)

            self._library.write(self._coll_name, his_data)
