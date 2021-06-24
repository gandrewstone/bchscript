import pdb
import sys
from binascii import hexlify, unhexlify
import hashlib
import bchscript.bchopcodes as bchopcodes
import bchscript.cashaddrutil as cashaddrutil
import bchscript.errors as err

if not "BCH_ADDRESS_PREFIX" in globals():  # don't initialize twice
    BCH_ADDRESS_PREFIX = None

BCH_TESTNET = "bchtest:"
BCH_MAINNET = "bitcoincash:"
BCH_REGTEST = "bchreg:"
BCH_ANYNET = None


def ScriptifyData(tmp):
    if type(tmp) is list:
        ret = []
        for t in tmp:
            ret.append(ScriptifyData(t))
        return b"".join(ret)

    if 1:
        ret = []
        if type(tmp) is str:
            tmp = bytes(tmp,"utf-8")
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

def ScriptifyNumber(num):
    if num == 0:
        return bytes([0])
    elif num < 17:
        return bytes([num+0x80])
    elif num < 256:
        return ScriptifyData(bytes([num]))
    elif num < 65536:
        return ScriptifyData(num.to_bytes(2, byteorder="little"))
    elif num < (1<<32):
        return ScriptifyData(num.to_bytes(4, byteorder="little"))
    else:
        return ScriptifyData(num.to_bytes(8, byteorder="little"))

def sha256(msg):
    """Return the sha256 hash of the passed data.  Non binary data is automatically converted

    >>> hexlify(sha256("e hat eye pie plus one is O"))
    b'c5b94099f454a3807377724eb99a33fbe9cb5813006cadc03e862a89d410eaf0'
    """
    msg = anything2bytes(msg)
    return hashlib.new('sha256', msg).digest()


def hash256(s):
    """Return the double SHA256 hash (what bitcoin typically uses) of the passed data.  Non binary data is automatically converted

    >>> hexlify(hash256("There was a terrible ghastly silence".encode()))
    b'730ac30b1e7f4061346277ab639d7a68c6686aeba4cc63280968b903024a0a40'
    """
    return sha256(sha256(s))


def hash160(msg):
    """RIPEME160(SHA256(msg)) -> bytes"""
    h = hashlib.new('ripemd160')
    msg = anything2bytes(msg)
    h.update(hashlib.sha256(msg).digest())
    return h.digest()


def blake2b(msg, len=32):
    msg = anything2bytes(msg)
    return hashlib.blake2b(msg, digest_size=len).digest()


def listify(obj):
    """wrap a list around something, if it is not currently a list"""
    if type(obj) is list:
        return obj
    return [obj]


def templatedJoin(listOfData):
    ret = [b""]
    # join binary strings, preserve other types as separate items
    for l in listOfData:
        if type(l) is bytes and type(ret[-1]) is bytes:
            ret[-1] = ret[-1] + l
        else:
            ret.append(l)

    # strip off the list if there is not template
    if len(ret) == 1 and type(ret[0]) is bytes:
        ret = ret[0]
    return ret

def applyTemplate(template, **kwargs):
    if type(template) is bytes:  # its already raw bytes, nothing to do
        return template
    applied = []
    for t in template:
        if type(t) is str:
            if t[0] is '$':
                t = kwargs.get(t[1:], t)  # Use the binding or the name if there is no binding
                applied.append(t)
            elif t[0] is '@':
                applied.append(t)
            else:
                raise err.Output("bad template")
        else:
            applied.append(t)
    return applied


def script2bin(opcodes, showSatisfierItems=True, showTemplateItems=True):
    """Convert a program to a binary string"""
    if not type(opcodes) is list:
        opcodes = [opcodes]

    ret = []
    for opcode in opcodes:
        s = None
        if type(opcode) is str:
            if opcode[0] == "@":  # its an existing stack arg, so no-op
                s = opcode
            elif opcode[0] == "$":  # its an existing stack arg, so no-op
                s = opcode
            else:
                ret.append(opcode.encode("utf-8"))

        # serialize object to bytes
        elif hasattr(opcode, "scriptify"):
            s = opcode.scriptify()
        elif hasattr(opcode, "serialize"):
            s = opcode.serialize()
        elif type(opcode) is int:
            s = ScriptifyNumber(opcode)
        elif type(opcode) is bytes:  # encode the command to push data onto stack, then the data
            s = ScriptifyData(opcode)
        else:
            assert 0, "Not fully compiled: %s" % opcode

        if type(s) is str:
            if s[0] == "@":  # its an existing stack arg, so no-op
                if showSatisfierItems:
                    ret.append(s)
            elif s[0] == "$":  # its an existing stack arg, so no-op
                if showTemplateItems:
                    ret.append(s)
            else:
                ret.append(opcode.encode("utf-8"))
        else:
            if not s is None:
                ret.append(s)

    return templatedJoin(ret)


def script2hex(opcodes):
    """Convert a program to a hex string suitable for RPC"""
    ret = []
    tobytes = []
    for phrases in opcodes:
        for bins in script2bin(phrases):
            if type(bins) is int:
                tobytes.append(bins)
            else:
                # If there's some bytecode ready to convert, do it now before including a template param
                if len(tobytes) > 0:
                    ret.append(hexlify(bytes(tobytes)).decode("utf-8"))
                    tobytes = []
                if type(bins) is bytes:
                    if bins != b"":
                        ret.append(hexlify(bins).decode("utf-8"))
                elif isinstance(bins, str):
                    ret.append(bins)  # Its a template parameter
                elif type(bins) is int:
                    tobytes.append(bins)
    # Any final bytes to convert to hex?
    if len(tobytes) > 0:
        ret.append(hexlify(bytes(tobytes)).decode("utf-8"))
    return ret


# Deserialize from a hex string representation (eg from RPC)
def FromHex(obj, hex_string):
    obj.deserialize(BytesIO(unhexlify(hex_string.encode('ascii'))))
    return obj

# Convert a binary-serializable object to hex (eg for submission via RPC)


def ToHex(obj):
    if hasattr(obj, 'serialize'):  # transform objects to binary
        obj = obj.serialize()
    if type(obj) is bytes:
        return hexlify(obj).decode('ascii')
    if type(obj) is str:
        if obj[0] == '@':  # include satisfier script inputs
            return "_" + obj + "_"
        if obj[0] == '$':  # include template params
            return "_" + obj + "_"
    
    if type(obj) is list:
        r = []
        for i in obj:
            if not i:   # skip empty
                continue
            r.append(ToHex(i))
        return "".join(r)
    return hexlify(obj.serialize()).decode('ascii')


class InvalidAddress(Exception):
    """Raised on generic invalid base58 data, such as bad characters.
    Checksum failures raise Base58ChecksumError specifically.
    """
    pass


def bitcoinAddress2bin(btcAddress):
    """convert a bitcoin address to binary data capable of being put in a CScript"""
    # chop the version and checksum out of the bytes of the address
    if ":" in btcAddress:
        pfx, addr = btcAddress.split(":")
        decoded = cashaddrutil.b32decode(addr)
        if not cashaddrutil.verify_checksum(pfx, decoded):
            raise InvalidAddress('Bad cash address checksum')
        converted = cashaddrutil.convertbits(decoded, 5, 8)
        return bytes(converted[1:21])  # 0 is address type, last 6 are checksum
    else:
        return decodeBase58(btcAddress)[1:-4]


B58_DIGITS = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def decodeBase58(s):
    """Decode a base58-encoding string, returning bytes"""
    if not s:
        return b''

    # Convert the string to an integer
    n = 0
    for c in s:
        n *= 58
        if c not in B58_DIGITS:
            raise InvalidAddress('Character %r is not a valid base58 character' % c)
        digit = B58_DIGITS.index(c)
        n += digit

    # Convert the integer to bytes
    h = '%x' % n
    if len(h) % 2:
        h = '0' + h
    res = unhexlify(h.encode('utf8'))

    # Add padding back.
    pad = 0
    for c in s[:-1]:
        if c == B58_DIGITS[0]:
            pad += 1
        else:
            break
    return b'\x00' * pad + res


def encodeBase58(b):
    """Encode bytes to a base58-encoded string"""

    # Convert big-endian bytes to integer
    n = int('0x0' + hexlify(b).decode('utf8'), 16)

    # Divide that integer into bas58
    res = []
    while n > 0:
        n, r = divmod(n, 58)
        res.append(B58_DIGITS[r])
    res = ''.join(res[::-1])

    # Encode leading zeros as base58 zeros
    czero = b'\x00'
    if sys.version > '3':
        # In Python3 indexing a bytes returns numbers, not characters.
        czero = 0
    pad = 0
    for c in b:
        if c == czero:
            pad += 1
        else:
            break
    return B58_DIGITS[0] * pad + res


def encodeBitcoinAddress(prefix, data):
    data2 = prefix + data
    cksm = hash256(data2)[:4]
    data3 = data2 + cksm
    b58 = encodeBase58(data3)
    return b58


def anything2bytes(msg):
    if type(msg) is int:
        msg = bytes([msg])
    if type(msg) is str:
        msg = msg.encode("utf-8")
    return msg

def reportBadStatement(tokens, n, symbols, printIt=True):
    s = "ERROR: Bad statement or undefined symbol: %s\n" % tokens[n]
    s+= "    Known symbols: %s\n" % list(filter(lambda x: type(x) is str, symbols.keys()))
    s+= "    Context: %s\n" % tokens[n-10:n+10]
    if printIt: print(s)
    return s

def warn(s):
    print(s, file=sys.stderr)
