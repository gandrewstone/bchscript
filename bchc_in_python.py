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

def Thexlify(tpl):
    if type(tpl) is list:
        ret = []
        for t in tpl:
            if type(t) is bytes:
                ret.append(hexlify(t).decode())
            else:
                ret.append(t.name)
        return str(ret)
    else:
        return hexlify(tpl).decode()

def dumpScript(s):
    print("Output script:")
    print(prettyPrint(s["constraint"]))
    print("Hex: " + Thexlify(script2bin(s["constraint"])))
    print("\nSpend script:")
    print(prettyPrint(s["satisfier"]))
    print("Hex: " + Thexlify(script2bin(s["satisfier"])))

    if "redeem" in s:
        print("\nRedeem script:")
        print(prettyPrint(s["redeem"]))

import struct

def ser_string(s):
    """convert a string into an array of bytes (in the bitcoin network format)

       >>> ser_string("The grid bug bites!  You get zapped!".encode())
       b'$The grid bug bites!  You get zapped!'
    """
    if len(s) < 253:
        return struct.pack("B", len(s)) + s
    elif len(s) < 0x10000:
        return struct.pack("<BH", 253, len(s)) + s
    elif len(s) < 0x100000000:
        return struct.pack("<BI", 254, len(s)) + s
    return struct.pack("<BQ", 255, len(s)) + s


def Test():
    inp = open("examples/math.bch", "r")
    ret = compile(inp)

    out = script2bin(ret["out0"]["constraint"])
    inp = script2bin(ret["inp"]["constraint"])
    
    f = open("aflinput1.bin","wb")
    flags = 0
    version = 0x1000
    result = struct.pack("<I",version)
    f.write(result)
    result = struct.pack("<I",flags)
    f.write(result)
    f.write(ser_string(inp))
    f.write(ser_string(out))
    f.close()

    for (key, val) in ret.items():
        print("\n\n%s:\n" % key)
        dumpScript(val)


if __name__== "__main__":
    print("This is intended to show how bchscript can be used within python, not be run from the command line.\n\n")
    Test()
