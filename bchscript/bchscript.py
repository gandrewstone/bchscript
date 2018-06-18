#!/bin/python3
import pdb
import re
from bchscript.bchutil import *
from bchscript.bchprimitives import *
from bchscript.bchimmediates import immediates, BchAddress, HexNumber


class ParserError(Exception):
    pass


multiTokens = ["0x", "->", "...", "bchtest:", "bitcoincash:", "bchreg:"]
unitaryTokens = """,./?~`#$%^&*()-+=\|}{[]'";:"""

bchStatements = primitives
bchStatements.update(immediates)


def statementConsumer(tokens, n, localSymbols):
    stmts = []
    while 1:
        if n >= len(tokens):
            break
        try:
            i = int(tokens[n])  # Push a number onto the stack
            stmts.append(i)
            n += 1
        except:
            if tokens[n][0] == '"':  # Push data onto the stack
                stmts.append(tokens[n])
                n += 1
            elif tokens[n] in localSymbols:
                syms = copy.copy(bchStatements)
                syms.update(localSymbols)
                (n, obj) = localSymbols[tokens[n]].parse(tokens, n + 1, syms)
                stmts.append(obj)
            elif tokens[n] in bchStatements:
                syms = copy.copy(bchStatements)
                syms.update(localSymbols)
                (n, obj) = bchStatements[tokens[n]].parse(tokens, n + 1, syms)
                if obj.outputs:
                    localSymbols.update(obj.outputs)
                stmts.append(obj)
            else:
                break

    return (n, stmts)


SetStatementConsumerCallout(statementConsumer)


class Scriptify:
    def __init__(self):
        self.name = "scriptify!"
        self.statements = None
        self.args = []

    def parse(self, tokens, n, symbols=None):
        """
        default doesn't accept any other tokens
        """
        global bchStatements
        syms = copy.copy(bchStatements)
        if symbols:
            syms.update(symbols)

        assert tokens[n] == "("
        (n, self.args) = argsConsumer(tokens, n, syms)

        dup = copy.copy(self)
        dup.name = self.args[0].strip("'").strip('"')
        dup.statements = listify(self.args[1])
        return (n, dup)

    def compile(self, symbols):
        output = compileStatementList(self.statements, symbols)
        spend = self.solve(output)
        return (self.name, {"script": output, "spend": spend})

    def solve(self, pgm, n=0, end=None):
        if end is None:
            end = len(pgm)
        ret = []

        while n < end:
            item = pgm[n]
            if type(item) is str and item[0] == "@":
                ret.append(item)
                n += 1
                continue
            elif type(item) is SpendScriptItem:
                if not item.val is None:
                    ret.append(item.val)
                else:
                    ret.append(item.name)
                n += 1
            elif type(item) is str and item == "OP_IF":
                (els, endif) = condSection(n, pgm)
                ret.append([self.solve(pgm, n + 1, els - 1), self.solve(pgm, els + 1, endif - 1)])
                n = endif + 1
            else:
                n += 1
        return ret

def RemoveSpendParams(script):
    ret = []
    for s in script:
        if not type(s) is SpendScriptItem:
            ret.append(s)
    return ret
    

class P2shify(Scriptify):
    def __init__(self):
        Scriptify.__init__(self)
        self.name = "p2shify!"
        self.statements = None

    def compile(self, symbols):
        redeem = compileStatementList(self.statements, symbols)
        redeemCleaned = RemoveSpendParams(redeem)
        redeemBin = script2bin(redeemCleaned)
        spend = self.solve(redeem)
        spend.append(redeemBin)
        scriptHash = hash160(redeemBin)
        p2sh = [primitives["OP_HASH160"], scriptHash, primitives["OP_EQUAL"]]
        return (self.name, {"script": p2sh, "spend": spend, "redeem": redeemCleaned})


class Define:
    def __init__(self):
        self.name = "def"
        self.statements = None
        self.args = None

    def matchArgs(self, bindings):
        """Match passed arguments with their definitions to produce a dictionary of { symbol: binding } pairs
        """
        ret = {}
        count = 0
        for b in bindings:
            a = self.args[count]
            if type(b) == list:
                pdb.set_trace()
            ret[a] = b
            count += 1
        return ret

    def compile(self, invocation):
        if invocation is None:  # a raw define produces no output, it must be applied
            return []          # note that a 0-arg invocation will be an empty dict
        return compileStatementList(self.statements, invocation)

    def parse(self, tokens, n, symbols=None):
        """
        default doesn't accept any other tokens
        """
        global bchStatements
        self.define = tokens[n]
        n += 1
        if tokens[n] == "(":
            (n, self.args) = paramsConsumer(tokens, n)
        if tokens[n] == "->":
            (n, self.results) = paramsConsumer(tokens, n + 1)
        assert tokens[n] == "{"
        n += 1
        (n, self.statements) = statementConsumer(tokens, n, self.args)
        assert tokens[n] == "}"
        tmp = Binding(self.define)
        cpy = copy.copy(self)
        tmp.instanceOf = cpy
        bchStatements[self.define] = tmp
        return (n + 1, cpy)


class Include:
    """Implement the include primitive"""

    def __init__(self):
        self.name = "def"
        self.statements = None

    def parse(self, tokens, n, symbols=None):
        filename = tokens[n].strip("'").strip('"')
        inp = open(filename, "r")
        newtokens = lex(inp)
        # insert the tokens of the included file at this point
        tokens[n + 1:n + 1] = newtokens
        return (n + 1, copy.copy(self))

    def compile(self, symbols):
        return []


topScope = {"def": Define(), "scriptify!": Scriptify(), "p2shify!": P2shify(), "include": Include()}


def topParser(tokens, n):
    stmts = []
    while tokens[n] in topScope:
#        print(tokens[n])
        (n, obj) = topScope[tokens[n]].parse(tokens, n + 1)
        stmts.append(obj)
        if n >= len(tokens):  # all done
            break
    if n < len(tokens):
        raise ParserError("""Parsing stopped at token %d: '%s'\ncontext:\n %s)""" %
                          (n, tokens[n], " ".join(tokens[n - 20:min(len(tokens), n + 20)])))
    return (n, stmts)


def separate(t):
    ret = []
    cur = []
    for tok in multiTokens:
        idx = t.find(tok)
        if idx != -1:
            pfx = separate(t[0:idx])
            sfx = separate(t[idx + len(tok):])
            return pfx + [tok] + sfx
    for c in t:
        if c in unitaryTokens:
            if cur:
                ret.append("".join(cur))
                cur = []
            ret.append(c)
        else:
            cur.append(c)
    if cur:
        ret.append("".join(cur))
    return ret


def lex(fin):
    ret = []
    for line in fin:
        tcomment = line.split("//")
        splitquotes = [x for x in re.split("( |\\\".*?\\\"|'.*?')", tcomment[0]) if x.strip()]
        # print(splitquotes)
        # pdb.set_trace()
        for sq in splitquotes:
            if sq[0] == '"' or sq[0] == "'":
                ret.append(sq)
            else:
                tspc = sq.split()
                for t in tspc:
                    tokens = separate(t)
                    # print(tokens)
                    ret += tokens
    return ret


def bchCompile(program):
    commands = []
    for p in program:
        temp = p.compile(None)
        commands.append(temp)

    ret = {}
    for c in commands:
        if type(c) is tuple:
            ret[c[0]] = c[1]
    return ret


def condSection(start, pgm):
    """find else and endif clauses"""
    nif = 0
    nelse = 0
    elsepos = None
    pos = start
    while pos < len(pgm):
        if pgm[pos] == "OP_IF":
            nif += 1
        elif pgm[pos] == "OP_ELSE":
            if nif == 1:
                elsepos = pos
        elif pgm[pos] == "OP_ENDIF":
            nif -= 1
            if nif == 0:
                return(elsepos, pos)
        pos += 1
    assert 0  # not closed


def prettyPrint(opcodes):
    """Convert a program to a human-readable string"""
    ret = []
    indent = 0
    for opcode in opcodes:
        if type(opcode) is str and opcode[0] == "@":
            continue
        if type(opcode) is str:
            opcode = '"' + opcode + '"'
        if type(opcode) is Primitive:
            opcode = opcode.name
        if type(opcode) is BchAddress:
            opcode = opcode.name
        if type(opcode) is HexNumber:
            opcode = opcode.name

        if opcode in ["OP_ELSE", "OP_ENDIF"]:
            indent -= 4
            
        if type(opcode) is bytes:
            ret.append(" " * indent + ToHex(opcode))
        else:
            ret.append(" " * indent + str(opcode))
        if opcode in ["OP_IF", "OP_ELSE"]:
            indent += 4
    return "\n".join(ret)


def compile(s):
    """Accepts either a string or an iterable of lines"""
    if type(s) is str:
        s = s.split("\n")
    tokens = lex(s)
    (n, program) = topParser(tokens, 0)
    result = bchCompile(program)
    return result


def main(fin, fout):
    tokens = lex(fin)
    print("LEX:\n", tokens, "\n\n")
    # pdb.set_trace()
    (n, program) = topParser(tokens, 0)
    print(tokens)
    print(program)
    print(len(tokens), n)
    result = bchCompile(program)
    if "main" in result:
        script = prettyPrint(result["main"]["script"])
        fout.write(script)
        print("Script Hex:")
        print(script2hex(result["main"]["script"]))
        solutions = result["main"]["spend"]
        print("\nScript:")
        print(script)
        print("\nSpend Script:")
        print(solutions)


def Test():
    #inp = open("test/simplecond.bch","r")
    # inp = open("test/atomicswap.bch","r")
    inp = open("test/simple.bch", "r")
    #inp = open("test/hexencode.bch","r")
    # inp = open("test.bch","r")
    #inp = open("test/immediates.bch","r")
    oup = open("solve.txt", "w")
    main(inp, oup)
    inp.close()
    oup.close()
