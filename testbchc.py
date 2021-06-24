#!/usr/bin/python3
import pdb
import re
import sys
import argparse
import io
import json

from bchscript.bchutil import *
from bchscript.bchprimitives import *
from bchscript.bchimmediates import immediates, BchAddress
from bchscript.bchscript import *

def Test():
    searchPath = ["examples"]
    #inp = open("test/simplecond.bch","r")
    inp = open("examples/atomicswap.bch","r")
    #inp = open("examples/simple.bch", "r")
    #inp = open("test/hexencode.bch","r")
    # inp = open("test.bch","r")
    #inp = open("test/immediates.bch","r")
    oup = open("solve.txt", "w")
    main(inp, oup, searchPath)
    inp.close()
    oup.close()
