from bchscript.bchutil import BCH_TESTNET, BCH_MAINNET, BCH_REGTEST, bitcoinAddress2bin
from bchscript.bchscript import compile, script2hex, script2bin, prettyPrint


def mode(m):
    global BCH_ADDRESS_PREFIX
    BCH_ADDRESS_PREFIX = m
    # print("setting bch network to '%s'" % BCH_ADDRESS_PREFIX)


__all__ = ["bchscript"]
