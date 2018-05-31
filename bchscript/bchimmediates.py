import pdb
import hashlib
import copy

from bchscript.bchutil import *
from bchscript.bchprimitives import Primitive


def evalParamsList(params, symbols):
    ret = []
    if params is None:
        return []  # parameter is not yet bound (passing a macro)
    for s in params:
        if type(s) is int:
            ret.append(s)
        elif type(s) is str:
            ret.append(s)
        else:
            temp = s.compile(symbols)
            if len(temp) == 1:
                temp = temp[0]
            ret.append(temp)
    return ret


class Immediate(Primitive):
    def __init__(self, name, evalFn=None, docstring=None):
        Primitive.__init__(self, name, None)
        self.evalFn = evalFn
        if docstring:
            self.__doc__ == docstring

    def compile(self, symbols, text=True):
        if self.params:
            p = evalParamsList(self.params, symbols)
        else:
            p = []

        ret = self.eval(p)
        return ret

    def eval(self, args):
        return self.evalFn(*args)


class P2shHashOf:
    def __init__(self):
        self.name = "p2shHashOf"
        self.statements = None

    def parse(self, tokens, n, symbols=None):
        """
        default doesn't accept any other tokens
        """
        global bchStatements
        if tokens[n] == "(":
            (n, self.statements) = statementConsumer(tokens, n + 1, symbols)
        assert tokens[n] == ")"
        return (n + 1, copy.copy(self))

    def compile(self, symbols):
        pdb.set_trace()
        return []


class BchAddress:
    def __init__(self, name="BCHaddress"):
        self.name = name

    def parse(self, tokens, n, symbols=None):
        assert BCH_ADDRESS_PREFIX == None or self.name == BCH_ADDRESS_PREFIX, "Incorrect address (%s) for this network (%s)" % (
            self.name, BCH_ADDRESS_PREFIX)

        obj = BchAddress()
        obj.name = self.name + tokens[n]  # the next token is the actual string address
        return (n + 1, obj)

    def compile(self, symbols):
        return [self]

    def scriptify(self):
        ret = []
        tmp = self.serialize()
        l = len(tmp)
        if l == 0:  # push empty value onto the stack
            ret.append(bytes([0]))
        elif l <= 0x4b:
            ret.append(bytes([l]))  # 1-75 bytes push # of bytes as the opcode
            ret.append(tmp)
        elif l < 256:
            ret.append(bytes([bchopcodes.opcode2bin["OP_PUSHDATA1"]]))
            ret.append(bytes([l]))
            ret.append(tmp)
        elif l < 65536:
            ret.append(bytes([bchopcodes.opcode2bin["OP_PUSHDATA2"]]))
            ret.append(bytes([l & 255, l >> 8]))  # little endian
            ret.append(tmp)
        else:  # bigger values won't fit on the stack anyway
            assert 0, "cannot push %d bytes" % l
        return b"".join(ret)

    def serialize(self):
        tmp = bitcoinAddress2bin(self.name)
        return tmp


immediates = {
    "hash160!": Immediate("hash160!", lambda x: hash160(script2bin(x)), "Immediately calculate the hash160 of the passed parameter"),
    "hash256!": Immediate("hash256!", hash256, "Immediately calculate the double sha256 of the passed parameter"),
    "sha256!": Immediate("sha256!", sha256, "Immediately calculate the sha256 of the passed parameter"),
    "blake2b256!": Immediate("blake2b256!", lambda x: blake2b(x, 32), "Immediately calculate the blake2b hash of the passed parameter with a 32 byte result"),
    "blake2b160!": Immediate("blake2b256!", lambda x: blake2b(x, 20), "Immediately calculate the blake2b hash of the passed parameter with a 20 byte result"),
    "p2shHash!": P2shHashOf(),
    BCH_TESTNET: BchAddress(BCH_TESTNET),
    BCH_MAINNET: BchAddress(BCH_MAINNET),
    BCH_REGTEST: BchAddress(BCH_REGTEST)
}
