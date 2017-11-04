# -*- coding: utf-8 -*-
import multiprocessing
from multiprocessing import Process

import tushare as ts

import backtradercn.strategies.ma as bsm
import backtradercn.tasks as btasks
from backtradercn.libs.log import logging

logger = logging.getLogger(__name__)


def back_test(stock):
    """
    Run back testing tasks via multiprocessing
    :return: None
    """

    task = btasks.Task(bsm.MATrendStrategy, stock)
    result = task.task()

    trading_days = result.get('trading_days')
    total_return_rate = result.get('total_return_rate')
    max_drawdown = result.get('max_drawdown')
    max_drawdown_period = result.get('max_drawdown_period')
    logger.debug(
        f'Stock {stock} back testing result, trading days: {trading_days:.2f}, '
        f'total return rate: {total_return_rate:.2f}, '
        f'max drawdown: {max_drawdown:.2f}, '
        f'max drawdown period: {max_drawdown_period:.2f}'
    )

    drawdown_points = result.get('drawdown_points')
    logger.debug('Draw down points:')
    for drawdown_point in drawdown_points:
        drawdown_point_dt = drawdown_point.get("datetime").isoformat()
        drawdown = drawdown_point.get('drawdown')
        drawdownlen = drawdown_point.get('drawdownlen')
        logger.debug(
            f'stock: {stock}, drawdown_point: {drawdown_point_dt}, '
            f'drawdown: {drawdown:.2f}, drawdownlen: {drawdownlen}'
        )


def main():
    top_hs300 = ts.get_hs300s()
    stock_pools = ts.get_hs300s()['code'].tolist() if 'code' in top_hs300 else []
    stock_pools = stock_pools[:5]
    processes = multiprocessing.cpu_count()
    # run subprocess in parallel, the number of processes is: `processes`
    for i in range(len(stock_pools) // processes + 1):
        chunk_start = i * processes
        chunk_end = (i + 1) * processes
        chunk_lst = stock_pools[chunk_start:chunk_end]
        logger.debug(f'back test the chunk list: {chunk_lst}')
        procs = []
        for stock in chunk_lst:
            proc = Process(target=back_test, args=(stock,))
            procs.append(proc)
            proc.start()
        for proc in procs:
            proc.join()


if __name__ == '__main__':
    # back_test('000651')
    main()
