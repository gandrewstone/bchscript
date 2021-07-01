#!/bin/python3
import pdb
import re
import sys
import os.path

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
        elif str(tokens[n])[0] == '"':  # Push data onto the stack
                stmts.append(tokens[n])
                n += 1
        elif str(tokens[n])[0] == '$':  # Template parameter, rip off the $ prefix
                stmts.append(TemplateParam(tokens[n]))
                n += 1
        elif str(tokens[n]) in localSymbols:
                syms = copy.copy(bchStatements)
                syms.update(localSymbols)
                (n, obj) = localSymbols[str(tokens[n])].parse(tokens, n + 1, syms)
                stmts.append(obj)
        elif str(tokens[n]) in bchStatements:
                syms = copy.copy(bchStatements)
                syms.update(localSymbols)
                (n, obj) = bchStatements[str(tokens[n])].parse(tokens, n + 1, syms)
                if obj.outputs:
                    localSymbols.update(obj.outputs)
                stmts.append(obj)
        else:
                if str(tokens[n]) != "}":  # expected closer so not a problem
                    print(tokens[n].locationEmacspy("{token} is not a statement"))
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

    def allSatisfiers(self, stack):
        for s in stack:
            if type(s) is str and s[0] != '@': return False
            if not type(s) is SpendScriptItem: return False
        return True

    def simStack(self, item, stack, altstack, satisfierStack):
        if type(item) is str:
            stack.append(item)
        elif isinstance(item, Immediate):
            stack.append(item)
        elif isinstance(item,SpendScriptItem):
            if not self.allSatisfiers(stack):  # If the stack isn't clean now, then a satisfier script (pre-executing) can't push the param onto the stack here (after this script has pushed something)
                raise Exception("Satisfier parameter misplaced: %s" % item.name, "")
            # Ok we could have run a satisfier script to have placed something on the stack here, so let's pretend that that happened.
            #satisfierStack.append(item)
            stack.append(item)
        elif isinstance(item, Primitive):
            ((consumed, produced), (altconsumed, altproduced)) = item.stackEffect(stack, altstack)
            removed = []
            altRemoved = []
            # TODO altstack
            if altconsumed > 0:
                altRemoved = altstack[-altconsumed:]
            if consumed > 0:
                removed = stack[-consumed:]
                del stack[-consumed:]
                for r in removed:
                    if isinstance(r,SpendScriptItem):
                        if not r.pushedOntoSatisfier:
                            r.pushedOntoSatisfier = True  # we will only push it once, and assume any other use is caused by duplication, etc
                            satisfierStack.insert(0, r)
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
            self.simStack(item, stack, altstack, ret)
            if isOpcode(item, "IF"):
                (els, endif) = condSection(n, pgm)
                # any satisfiers that are needed must be pushed before any satisfiers consumed by prior instructions so insert them at the beginning
                ret.insert(0,({1:self.solve(pgm, n + 1, els), 0:self.solve(pgm, els + 1, endif - 1)}))
                n = endif + 1
            else:
                n += 1
        # rev = reverseListsIn(ret)  # We need to reverse the direction of execution because the last item pushed onto the stack is on top
        return ret

def reverseListsIn(lst):
    print("reverse ", lst)
    ret = []
    for item in reversed(lst):
        if type(item) is list:
            ret.append(item) #  already reversed during recursive solver: reverseListsIn(item))
        elif type(item) is dict:
            rd = {}
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
                assert(false)
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
        cpy = copy.copy(self)
        if tokens[n] != "}":
            reportBadStatement(tokens, n, self.args)
            return (n+1, cpy) # sys.exit(1) # assert tokens[n] == "}"
        tmp = Binding(self.define)
        tmp.instanceOf = cpy
        bchStatements[self.define] = tmp
        return (n + 1, cpy)


class Include:
    """Implement the include primitive"""

    def __init__(self, searchPath=None):
        self.searchPath = searchPath
        self.name = "include"
        self.statements = None
        self.filename = None
        self.filepath = None

    def parse(self, tokens, n, symbols=None):
        self.filename = tokens[n].strip("'").strip('"')
        inp = None
        self.filepath = None
        dup = []
        for p in self.searchPath:
            try:
                if inp is None:
                    self.filepath = os.path.abspath(os.path.join(p, self.filename))
                    inp = open(self.filepath, "r")
                else:
                    potDup = os.path.abspath(os.path.join(p, self.filename))
                    if self.filepath != potDup and os.path.isfile(potDup):
                        dup.append(p)
            except FileNotFoundError as e:
                pass
        if inp is None:
            raise FileNotFoundError("Cannot find included file '%s' in search path '%s'" % (self.filename, self.searchPath))
        if len(dup):
            warn("Included file %s has duplicates here: %s" % (self.filepath, " ".join(dup)))
        newtokens = lex(inp, self.filepath)
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
    while str(tokens[n]) in topScope:
#        print(tokens[n])
        (n, obj) = topScope[str(tokens[n])].parse(tokens, n + 1)
        stmts.append(obj)
        if n >= len(tokens):  # all done
            break
    if n < len(tokens):
        raise ParserError("""Parsing stopped at token %d: '%s'\ncontext:\n %s)""" %
                          (n, tokens[n], " ".join(tokens[n - 20:min(len(tokens), n + 20)])))
    return (n, stmts)


def separate(t, filename, lineNum, pos):
    ret = []
    cur = []
    for tok in multiTokens:
        idx = t.find(tok)
        if idx != -1:
            pfx = separate(t[0:idx], filename, lineNum, pos)
            sfx = separate(t[idx + len(tok):], filename, lineNum, pos)
            return pfx + [TokenChunk(tok, filename, lineNum, idx)] + sfx
    for c in t:
        if c in unitaryTokens:
            if cur:
                tmp = "".join(cur)
                ret.append(TokenChunk(tmp, filename, lineNum, pos))
                pos += len(tmp)
                cur = []
            ret.append(c)
        else:
            cur.append(c)
    if cur:
        ret.append(TokenChunk("".join(cur), filename, lineNum, pos))
    return ret


def lex(fin, filename):  # =None):
    ret = []
    lineNum = 0
    for line in fin:
        lineNum+=1
        tcomment = line.split("//")
        splitquotes = [x for x in re.split("( |\\\".*?\\\"|'.*?')", tcomment[0]) if len(x) > 0]
        #print(splitquotes)
        pos = 0
        for sq in splitquotes:
            if sq[0] == '"' or sq[0] == "'":
                ret.append(TokenChunk(sq, filename, lineNum, pos))
            else:
                tspc = sq.split()
                for t in tspc:
                    tokens = separate(t, filename, lineNum, pos)
                    # print("Toks: ", tokens)
                    ret += tokens
            pos += len(sq)
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


def compile(s, searchPath, filename):
    """Accepts either a string or an iterable of lines"""
    if type(s) is str:
        s = s.split("\n")
    tokens = lex(s, filename)
    (n, program) = topParser(tokens, 0, searchPath)
    result = bchCompile(program)
    return result


def main(fin, fout, searchPath, filename):
    tokens = lex(fin, filename)
    print("LEX:\n", tokens, "\n\n")
    (n, program) = topParser(tokens, 0, searchPath)
    print(tokens)
    print(program)
    print(len(tokens), n)
    result = bchCompile(program)
    if "main" in result:
        constraint = result["main"]["constraint"]
        script = prettyPrint(constraint, False)
        fout.write(script)
        print("Constraint Script")
        print("  Script Hex:")
        constraintHex = script2bin(constraint, False)
        print("  ", constraintHex)
        constraintHex = script2hex(constraint)
        print("  ", constraintHex)
        print(script)

        print("\nSatisfier Script:")
        solutions = prettyPrint(result["main"]["satisfier"])
        print(solutions)

        print("\nCombined constraint script with satisfier pushes")
        script = prettyPrint(constraint)
        print(script)
