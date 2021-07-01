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
    searchPath = ["examples","test"]
    #inp = open("test/simplecond.bch","r")
    #inFilename = "examples/atomicswap.bch"
    inFilename = "test/testInclude.bch"
    
    #inp = open("examples/simple.bch", "r")
    #inp = open("test/hexencode.bch","r")
    # inp = open("test.bch","r")
    #inp = open("test/immediates.bch","r")
    oup = open("solve.txt", "w")

    inp = open(inFilename,"r")
    main(inp, oup, searchPath, inFilename)
    inp.close()
    oup.close()
