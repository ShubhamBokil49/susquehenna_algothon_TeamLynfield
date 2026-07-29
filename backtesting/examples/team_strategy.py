import numpy as np

PAIRS = [
    ("SMAH", "ILVX"),
    ("HUXZ", "ACAC"),
    ("HETT", "ULXY"),
    ("CTGI", "EELT"),
    ("MTNS", "BENI"),
    ("MHRM", "EAFC"),
    ("RTTH", "NAYO"),
    ("FWWG", "BLBT"),
    ("EORC", "NGTE"),
    ("AENO", "NWIG"),
    ("ALUT", "CCNS"),
    ("ACIX", "ITPA"),
    ("DIHO", "SPLZ"),
    ("GARI", "RCRI"),
]
# NOTE: ALGO deliberately excluded — it doesn't cointegrate with anything
# in the set (best p-value ~0.11, and its own price isn't mean-reverting
# either, ADF p~0.71), so a forced pair would be noise, not signal, despite
# its bigger $100k cap. Trading it needs a different edge (e.g. momentum),
# not pairs mean-reversion.

LOOKBACK = 100
ENTRY_Z = 2.0
EXIT_Z = 0.5
MAX_ALGO = 100_000
MAX_OTHER = 10_000

NAMES = None
_state = {}


def init(names):
    global NAMES
    NAMES = list(names)
    for a, b in PAIRS:
        _state[(a, b)] = 0


def _hedge_ratio(px_a, px_b):
    cov = np.cov(px_a, px_b)
    beta = cov[0, 1] / cov[1, 1]
    return beta


def getMyPosition(prcSoFar):
    global NAMES
    nInst, nt = prcSoFar.shape
    if NAMES is None:
        NAMES = "ALGO AENO LSST SRNA ELLT AMRP OTCS HETT HUXZ DUCT SMAH NPCK MSDP EORC CUBO HRET ANSO DIHO RTTH SPLZ NWIG MMBT MDGI AGVF RRES CTGI ALUT ACAC SRTX GARI RCRI ACIX CCNS MTNS IHOZ NAYO FWWG EELT HRND AETS ULXY BLBT BENI ITPA HTRK NGTE ILVX FCSG FARS MHRM EAFC".split()
        for a, b in PAIRS:
            _state.setdefault((a, b), 0)

    idx = {n: i for i, n in enumerate(NAMES)}
    pos = np.zeros(nInst)

    if nt < LOOKBACK + 1:
        return pos

    for a, b in PAIRS:
        if a not in idx or b not in idx:
            continue
        ia, ib = idx[a], idx[b]
        px_a = prcSoFar[ia, -LOOKBACK:]
        px_b = prcSoFar[ib, -LOOKBACK:]

        beta = _hedge_ratio(px_a, px_b)
        spread = px_a - beta * px_b
        mu, sigma = spread.mean(), spread.std()
        if sigma == 0:
            continue
        z = (spread[-1] - mu) / sigma

        cur = _state[(a, b)]
        if cur == 0:
            if z > ENTRY_Z:
                cur = -1
            elif z < -ENTRY_Z:
                cur = 1
        else:
            if abs(z) < EXIT_Z:
                cur = 0
        _state[(a, b)] = cur

        if cur == 0:
            continue

        cap_a = MAX_ALGO if ia == 0 else MAX_OTHER
        cap_b = MAX_ALGO if ib == 0 else MAX_OTHER
        price_a, price_b = px_a[-1], px_b[-1]

        dollar_a = cur * cap_a
        units_a = dollar_a / price_a
        dollar_b = -np.sign(cur) * min(cap_b, abs(beta) * cap_a)
        units_b = dollar_b / price_b

        pos[ia] += units_a
        pos[ib] += units_b

    return pos
