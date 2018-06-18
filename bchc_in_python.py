#!/usr/bin/python3
import pdb
import re
import sys
import argparse
import io

from bchscript.bchutil import *
from bchscript.bchprimitives import *
from bchscript.bchimmediates import immediates, BchAddress, ScriptifyData
from bchscript.bchscript import *

def Test():
    inp = open("examples/secretLock.bch", "r")
    ret = compile(inp)
    print("Output script:")
    print(prettyPrint(ret["main"]["script"]))
    print("Hex: " + hexlify(script2bin(ret["main"]["script"])).decode())
    print("\nSpend script:")
    print(prettyPrint(ret["main"]["spend"]))
    print("Hex: " + hexlify(script2bin(ret["main"]["spend"])).decode())

    print("\nRedeem script:")
    print(prettyPrint(ret["main"]["redeem"]))

if __name__== "__main__":
    print("This is intended to show how bchscript can be used within python, not be run from the command line.\n\n")
    Test()
