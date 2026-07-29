import numpy as np


def getMyPosition(prices):
    n_instruments = prices.shape[0]
    return np.zeros(n_instruments, dtype=int)
