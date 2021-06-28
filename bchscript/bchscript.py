#!/bin/python3
import pdb
import re
import sys
import traceback
import os.path

def excepthook(type, value, tb):
    print("\n'" + type.__name__ + "' Exception Raised:")
    # printed by print_exception: print(str(value))
    traceback.print_exception(type, value, tb)
    pdb.pm()
    print("exception")

sys.excepthook = excepthook

from bchscript.bchutil import *
from bchscript.bchprimitives import *
from bchscript.bchimmediates import Immediate, immediates, BchAddress, HexNumber


class ParserError(Exception):
    pass


multiTokens = ["0x", "->", "...", "bchtest:", "bitcoincash:", "bchreg:"]
unitaryTokens = """,./?~`#%^&*()-+=\|}{[]'";:"""

bchStatements = primitives
bchStatements.update(immediates)


def statementConsumer(tokens, n, localSymbols):
    stmts = []
    while 1:
        if n >= len(tokens):
            break
        try:
            i = int(tokens[n])  # Push a number onto the stack
            isAnInt = True
        except:
            isAnInt = False

        if isAnInt:
            stmts.append(i)
            n += 1
        elif tokens[n][0] == '"':  # Push data onto the stack
                stmts.append(tokens[n])
                n += 1
        elif tokens[n][0] == '$':  # Template parameter
                stmts.append(TemplateParam(tokens[n][1:]))
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
                if tokens[n] != "}":  # expected closer so not a problem
                    print("%s is not a statement" % tokens[n])
                break

    return (n, stmts)


SetStatementConsumerCallout(statementConsumer)


class Scriptify:
    def __init__(self):
        self.name = "scriptify!"
        self.statements = None
        self.args = []
        self.outputs = None

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
        try:
            dup.name = self.args[0].strip("'").strip('"')
        except AttributeError:
            raise ParserError("First parameter of scriptify! must be a string")
        dup.statements = listify(self.args[1])
        return (n, dup)

    def compile(self, symbols):
        output = compileStatementList(self.statements, symbols)
        spend = self.solve(output)
        return (self.name, {"constraint": output, "satisfier": spend})

    def solve_old(self, pgm, n=0, end=None):
        """Given a program, figure out the satisfier scripts"""
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
                    ret.append(item.scriptify())
                n += 1
            elif type(item) is str and item == "OP_IF":
                (els, endif) = condSection(n, pgm)
                ret.append([self.solve(pgm, n + 1, els - 1), self.solve(pgm, els + 1, endif - 1)])
                n = endif + 1
            else:
                n += 1
        return ret

    def allSatisfiers(self, stack):
        for s in stack:
            if type(s) is str and s[0] != '@': return False
            if not type(s) is SpendScriptItem: return False
        return True

    def simStack(self, item, stack, altstack, satisfierStack):
        if type(item) is str:
            stack.append(item)
        elif type(item) is Immediate:
            stack.append(item)
        elif type(item) is SpendScriptItem:
            if not self.allSatisfiers(stack):  # If the stack isn't clean now, then a satisfier script (pre-executing) can't push the param onto the stack here (after this script has pushed something)
                raise Exception("Satisfier parameter misplaced: %s" % item.name, "")
            # Ok we could have run a satisfier script to have placed something on the stack here, so let's pretend that that happened.
            satisfierStack.append(item)
            stack.append(item)
        elif type(item) is Primitive:
            ((consumed, produced), (altconsumed, altproduced)) = item.stackEffect(stack, altstack)
            removed = []
            altRemoved = []
            # TODO altstack
            if altconsumed > 0:
                altRemoved = altstack[-altconsumed:]
            if consumed > 0:
                removed = stack[-consumed:]
                del stack[-consumed:]
            if produced > 0:
                # Put placeholders onto the stack for what this opcode did
                for i in range(0,produced):
                    stack.append(ResultData(i, item, removed, altRemoved))  # assumes all opcodes that read a stack element are specified as if they consume and replace that item

    def solve(self, pgm, n=0, end=None, stack=None, altstack = None):
        """Given a program, figure out the satisfier scripts"""
        if stack is None:
            stack = []
        if altstack is None:
            altstack = []
        if end is None:
            end = len(pgm)
        ret = []
        while n < end:
            item = pgm[n]
            if isOpcode(item, "IF"):
                (els, endif) = condSection(n, pgm)
                ret.append({1:self.solve(pgm, n + 1, els - 1), 0:self.solve(pgm, els + 1, endif - 1)})
                n = endif + 1
            else:
                self.simStack(item, stack, altstack, ret)
                n += 1
        rev = reverseListsIn(ret)  # We need to reverse the direction of execution because the last item pushed onto the stack is on top
        return rev

def reverseListsIn(lst):
    print("reverse ", lst)
    ret = []
    for item in reversed(lst):
        if type(item) is list:
            ret.append(item) #  already reversed during recursive solver: reverseListsIn(item))
        elif type(item) is dict:
            rd = {}
            pdb.set_trace()
            for (k,v) in item.items():
                rd[k] = v # already reversed during recursive solver: reverseListsIn(v)
            ret.append(rd)
        else:
            ret.append(item)
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
        self.outputs = None

    def compile(self, symbols):
        redeem = compileStatementList(self.statements, symbols)
        redeemCleaned = RemoveSpendParams(redeem)
        redeemBin = script2bin(redeemCleaned)
        spend = self.solve(redeem)
        spend.append(redeemBin)
        if type(redeemBin) is list:  # Its template so I can't simplify further
            scriptHash = "hash160(%s)" % str(redeemBin)
        else:
            scriptHash = hash160(redeemBin)
        p2sh = [primitives["OP_HASH160"], scriptHash, primitives["OP_EQUAL"]]
        return (self.name, {"constraint": p2sh, "satisfier": spend, "redeem": redeemCleaned})


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
        if tokens[n] != "}":
            reportBadStatement(tokens, n, self.args)
            assert tokens[n] == "}"
        tmp = Binding(self.define)
        cpy = copy.copy(self)
        tmp.instanceOf = cpy
        bchStatements[self.define] = tmp
        return (n + 1, cpy)


class Include:
    """Implement the include primitive"""

    def __init__(self, searchPath=None):
        self.searchPath = searchPath
        self.name = "include"
        self.statements = None

    def parse(self, tokens, n, symbols=None):
        filename = tokens[n].strip("'").strip('"')
        inp = None
        inpfname = None
        dup = []
        for p in self.searchPath:
            try:
                if inp is None:
                    inpfname = os.path.abspath(os.path.join(p, filename))
                    inp = open(inpfname, "r")
                else:
                    potDup = os.path.abspath(os.path.join(p, filename))
                    if inpfname != potDup and os.path.isfile(potDup):
                        dup.append(p)
            except FileNotFoundError as e:
                pass
        if inp is None:
            raise FileNotFoundError("Cannot find included file '%s' in search path '%s'" % (filename, self.searchPath))
        if len(dup):
            warn("Included file %s has duplicates here: %s" % (inpfname, " ".join(dup)))
        newtokens = lex(inp)
        # insert the tokens of the included file at this point
        tokens[n + 1:n + 1] = newtokens
        return (n + 1, copy.copy(self))

    def compile(self, symbols):
        return []


topScope = {"def": Define(), "scriptify!": Scriptify(), "p2shify!": P2shify(), "include": Include()}

bchStatements.update({"scriptify!": Scriptify(), "p2shify!": P2shify()})

def topParser(tokens, n, searchPath):
    stmts = []
    topScope["include"] = Include(searchPath)
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
        #print(splitquotes)
        for sq in splitquotes:
            if sq[0] == '"' or sq[0] == "'":
                ret.append(sq)
            else:
                tspc = sq.split()
                for t in tspc:
                    tokens = separate(t)
                    # print("Toks: ", tokens)
                    ret += tokens
    return ret


def bchCompile(program):
    commands = []
    for p in program:
        temp = p.compile(None)
        commands.append(temp)

    # pdb.set_trace()
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
        item = pgm[pos]
        if isOpcode(item, "IF"):
            nif += 1
        elif isOpcode(item, "ELSE"):
            if nif == 1:
                elsepos = pos
        elif isOpcode(item, "ENDIF"):
            nif -= 1
            if nif == 0:
                return(elsepos, pos)
        pos += 1
    assert 0  # not closed


def prettyPrint(opcodes, showSatisfierItems=True, showTemplateItems=True, indent = 0):
    """Convert a program to a human-readable string"""
    ret = []
    indent = 0
    for opcode in opcodes:
        # Handle satisfier items
        if type(opcode) is SpendScriptItem:
            if showSatisfierItems:
                ret.append(" " * indent + opcode.scriptify())
            continue
        elif type(opcode) is str and opcode[0] == "@":
            if showSatisfierItems:
                ret.append(" " * indent + opcode)
            continue

        # Handle template variables
        elif type(opcode) is TemplateParam:
            if showSatisfierItems:
                ret.append(" " * indent + opcode.scriptify())
            continue
        elif type(opcode) is str and opcode[0] == "$":
            if showTemplateItems:
                ret.append(" " * indent + opcode)
            continue
        elif type(opcode) is list: # Script bifurcates (satisfier scripts)
            paths = []
            for fork in opcode:
                paths.append(prettyPrint(fork,showSatisfierItems, showTemplateItems, indent = indent + 1))
            ret.append("[")
            for p in paths:
                for s in p.split("\n"):
                    ret.append(" " * (2*(indent+1)) + s)
                if p != paths[-1]: ret.append(",")
            ret.append("]")
            continue

        if type(opcode) is str:
            if opcode[0] == '"' or opcode[0] == "'":
                pass
            else:
                opcode = '"' + opcode + '"'
        if (hasattr(opcode, "str")):
            opcode = opcode.str()
        if type(opcode) is Primitive:
            opcode = opcode.name
        if type(opcode) is BchAddress:
            opcode = opcode.name
        if type(opcode) is HexNumber:
            opcode = opcode.name

        if opcode in ["ELSE", "ENDIF"]:
            indent -= 4

        if type(opcode) is bytes:
            ret.append(" " * indent + ToHex(opcode))
        else:
            ret.append(" " * indent + str(opcode))
        if opcode in ["IF", "ELSE"]:
            indent += 4
    return recursiveList2String(ret)  # "\n".join(ret)

def recursiveList2String(lstParam, indent = 0):
    lst = lstParam.copy()
    for i in range(0,len(lst)):
        l = lst[i]
        if type(l) is list:
            lst[i:i+1] = ["[", ",\n".join(recursiveList2String), "]"]
    return "\n".join(lst)


def compile(s, searchPath):
    """Accepts either a string or an iterable of lines"""
    if type(s) is str:
        s = s.split("\n")
    tokens = lex(s)
    (n, program) = topParser(tokens, 0, searchPath)
    result = bchCompile(program)
    return result


def main(fin, fout, searchPath):
    tokens = lex(fin)
    print("LEX:\n", tokens, "\n\n")
    # pdb.set_trace()
    (n, program) = topParser(tokens, 0, searchPath)
    print(tokens)
    print(program)
    print(len(tokens), n)
    result = bchCompile(program)
    if "main" in result:
        constraint = result["main"]["constraint"]
        script = prettyPrint(constraint)
        fout.write(script)
        print("Script Hex:")
        constraintHex = script2hex(constraint)
        print(constraintHex)
        solutions = prettyPrint(result["main"]["satisfier"])
        print("\nConstraint Script:")
        print(script)
        print("\nSatisfier Script:")
        print(solutions)
