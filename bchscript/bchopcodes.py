
def ifBifurcation(stack):
    return [stack, copy.copy(stack)]

def ifDupBifurcation(stack):
    raise "unimplemented"
    return [stack, copy.copy(stack)]

def notIfBifurcation(stack):
    raise "unimplemented"

def unspendable(stack):
    raise "Unspendable"
    return None

def sim2Rot(stack):
    raise "unimplemented"

def sim2Swap(stack):
    raise "unimplemented"

def simNip(stack):
    raise "unimplemented"

def simOver(stack):
    raise "unimplemented"

def simPick(stack):
    raise "unimplemented"

def simRoll(stack):
    raise "unimplemented"

def simRot(stack):
    raise "unimplemented"
def simSwap(stack):
    raise "unimplemented"
def simTuck(stack):
    raise "unimplemented"
def simMultisig(stack):
    raise "unimplemented"
def simOpExec(stack):
    raise "unimplemented"

def opcode2bin(name):
    return opcodeData[name][0]

opcodeData = {
    # name : (push value, stack consumed, stack produced, simulation function)
    "OP_0": (0x00, 0, 1, None),
    "OP_FALSE": (0x00, 0, 1, None),
    "OP_PUSHDATA1": (0x4c, 0, 1, None),
    "OP_PUSHDATA2": (0x4d, 0, 1, None),
    "OP_PUSHDATA4": (0x4e, 0, 1, None),
    "OP_1NEGATE": (0x4f, 0, 1, None),
    "OP_RESERVED": (0x50, 0, 1, None),
    "OP_1": (0x51, 0, 1, None),
    "OP_TRUE": (0x51, 0, 1, None),
    "OP_2": (0x52, 0, 1, None),
    "OP_3": (0x53, 0, 1, None),
    "OP_4": (0x54, 0, 1, None),
    "OP_5": (0x55, 0, 1, None),
    "OP_6": (0x56, 0, 1, None),
    "OP_7": (0x57, 0, 1, None),
    "OP_8": (0x58, 0, 1, None),
    "OP_9": (0x59, 0, 1, None),
    "OP_10": (0x5a, 0, 1, None),
    "OP_11": (0x5b, 0, 1, None),
    "OP_12": (0x5c, 0, 1, None),
    "OP_13": (0x5d, 0, 1, None),
    "OP_14": (0x5e, 0, 1, None),
    "OP_15": (0x5f, 0, 1, None),
    "OP_16": (0x60, 0, 1, None),

    # control
    "OP_NOP": (0x61, 0, 0, None),
    # "OP_VER": (0x62,
    "OP_IF": (0x63, 1, 0, ifBifurcation),
    "OP_NOTIF": (0x64, 1, 0, notIfBifurcation),
    # "OP_VERIF": (0x65,
    # "OP_VERNOTIF": (0x66,
    "OP_ELSE": (0x67, 0, 0, None),
    "OP_ENDIF": (0x68, 0, 0, None),
    "OP_VERIFY": (0x69, 1, 0, None),
    "OP_RETURN": (0x6a, 0, 0, unspendable),

    # stack ops
    "OP_TOALTSTACK": (0x6b, 1, 0, None),
    "OP_FROMALTSTACK": (0x6c, 0, 1, None),
    "OP_2DROP": (0x6d, 2, 0, None),
    "OP_2DUP": (0x6e, 0, 2, None),
    "OP_3DUP": (0x6f, 0, 3, None),
    "OP_2OVER": (0x70, 0, 2, None),
    "OP_2ROT": (0x71, 0, 0, sim2Rot),
    "OP_2SWAP": (0x72, 0, 0, sim2Swap),
    "OP_IFDUP": (0x73, 0, 0, ifDupBifurcation),
    "OP_DEPTH": (0x74, 0, 1, None),
    "OP_DROP": (0x75, 1, 0, None),
    "OP_DUP": (0x76, 0, 1, None),
    "OP_NIP": (0x77, None, 0, simNip),
    "OP_OVER": (0x78, 0, 1, simOver),
    "OP_PICK": (0x79, 0, 1, simPick),
    "OP_ROLL": (0x7a, None, None, simRoll),
    "OP_ROT": (0x7b, None, None, simRot),
    "OP_SWAP": (0x7c, None, None, simSwap),
    "OP_TUCK": (0x7d, None, None, simTuck),

    # splice ops
    "OP_CAT": (0x7e, 2, 1, None),
    "OP_SPLIT": (0x7f, 2, 2, None),
    "OP_NUM2BIN": (0x80, 2, 1, None),
    "OP_BIN2NUM": (0x81, 1, 1, None),
    "OP_SIZE": (0x82, 0, 1, None),

    # bit logic
    "OP_INVERT": (0x83, 1, 1, unspendable),
    "OP_AND": (0x84, 2, 1, None),
    "OP_OR": (0x85, 2, 1, None),
    "OP_XOR": (0x86, 2, 1, None),
    "OP_EQUAL": (0x87, 2, 1, None),
    "OP_EQUALVERIFY": (0x88, 2, 0, None),
    "OP_RESERVED1": (0x89, 0, 0, unspendable),
    "OP_RESERVED2": (0x8a, 0, 0, unspendable),

    # numeric
    "OP_1ADD": (0x8b, 1, 1, None),
    "OP_1SUB": (0x8c, 1, 1, None),
    "OP_2MUL": (0x8d, 1, 1, None),
    "OP_2DIV": (0x8e, 1, 1, None),
    "OP_NEGATE": (0x8f, 1, 1, None),
    "OP_ABS": (0x90, 1, 1, None),
    "OP_NOT": (0x91, 1, 1, None),
    "OP_0NOTEQUAL": (0x92, 1, 1, None),

    "OP_ADD": (0x93, 2, 1, None),
    "OP_SUB": (0x94, 2, 1, None),
    "OP_MUL": (0x95, 2, 1, None),
    "OP_DIV": (0x96, 2, 1, None),
    "OP_MOD": (0x97, 2, 1, None),
    "OP_LSHIFT": (0x98, 2, 1, None),
    "OP_RSHIFT": (0x99, 2, 1, None),

    "OP_BOOLAND": (0x9a, 2, 1, None),
    "OP_BOOLOR": (0x9b, 2, 1, None),
    "OP_NUMEQUAL": (0x9c, 2, 1, None),
    "OP_NUMEQUALVERIFY": (0x9d, 2, 0, None),
    "OP_NUMNOTEQUAL": (0x9e, 2, 1, None),
    "OP_LESSTHAN": (0x9f, 2, 1, None),
    "OP_GREATERTHAN": (0xa0, 2, 1, None),
    "OP_LESSTHANOREQUAL": (0xa1, 2, 1, None),
    "OP_GREATERTHANOREQUAL": (0xa2, 2, 1, None),
    "OP_MIN": (0xa3, 2, 1, None),
    "OP_MAX": (0xa4, 2, 1, None),

    "OP_WITHIN": (0xa5, 3, 1, None),

    # crypto
    "OP_RIPEMD160": (0xa6, 1, 1, None),
    "OP_SHA1": (0xa7, 1, 1, None),
    "OP_SHA256": (0xa8, 1, 1, None),
    "OP_HASH160": (0xa9, 1, 1, None),
    "OP_HASH256": (0xaa, 1, 1, None),
    "OP_CODESEPARATOR": (0xab, 0, 0, None),
    "OP_CHECKSIG": (0xac, 2, 1, None),
    "OP_CHECKSIGVERIFY": (0xad, 2, 0, None),
    "OP_CHECKMULTISIG": (0xae, None, 1, simMultisig),
    "OP_CHECKMULTISIGVERIFY": (0xaf, None, 0, simMultisig),

    # expansion
    "OP_NOP1": (0xb0, 0, 0, None),
    "OP_CHECKLOCKTIMEVERIFY": (0xb1, 0, 0, None),
    "OP_CHECKSEQUENCEVERIFY": (0xb2, 0,0, None),
    "OP_NOP4": (0xb3, 0, 0, None),
    "OP_NOP5": (0xb4, 0, 0, None),
    "OP_NOP6": (0xb5, 0, 0, None),
    "OP_NOP7": (0xb6, 0, 0, None),
    "OP_NOP8": (0xb7, 0, 0, None),
    "OP_NOP9": (0xb8, 0, 0, None),
    "OP_NOP10": (0xb9, 0, 0, None),

    #"OP_DATASIGVERIFY": (0xbb
    "OP_CHECKDATASIG": (0xba, 3, 1, None),
    "OP_CHECKDATASIGVERIFY": (0xbb, 3, 0, None)
}


nxcOpcode2bin = {
    "OP_BIN2BIGNUM": (0xec, 1, 1, None),
    "OP_BIGNUM2BIN": (0x80, 2, 1, None),
    "OP_EXEC": (0xed, None, None, simOpExec), # code param1...paramN N_Params M_Returns OP_EXEC => ret1...retN
    "OP_GROUP": (0xee, 2, 0, None),
    "OP_TEMPLATE": (0xef, 2, 0, None),
}
