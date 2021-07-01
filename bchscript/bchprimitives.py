import pdb
import copy
import bchscript.bchopcodes as bchopcodes
import bchscript.errors as err
from bchscript.bchutil import *

statementConsumerCallout = None


class TemplateParam():
    def __init__(self, name):
        if type(name) is TokenChunk:
            self.name = str(name)
            self.filename = name.filename
            self.line = name.line
            self.pos = name.pos
        else:
            self.name = name
            self.line = None
            self.pos = None
            self.filename = None
        if self.name[0] == "$":  # strip off the template indicator
            self.name = self.name[1:]
    def compile(self, symbols=None):
        """Compile into a list of statements, given an input substitution (symbol) table"""
        return [self]  # Template params pass thru compilation

    def scriptify(self):
        return "$" + self.name

def SetStatementConsumerCallout(t):
    global statementConsumerCallout
    statementConsumerCallout = t


def compileStatementList(statements, symbols):
    ret = []
    for s in statements:
        if type(s) in [int, str, bytes]:
            ret.append(s)
        else:
            ret.extend(s.compile(symbols))
    return ret


def compileParamsList(params, symbols):
    ret = []
    if params is None:
        return []  # parameter is not yet bound (passing a macro)
    for s in params:
        if type(s) is int:
            ret.append(s)
        elif type(s) is str:
            ret.append(s)
        elif type(s) is TokenChunk:
            ret.append(s)
        else:
            temp = s.compile(symbols)
            if type(temp) == list:
                ret.extend(temp)
            else:
                ret.append(temp)
    return ret


def isInt(obj):
    if type(obj) is TokenChunk:
        obj = str(obj)

    try:
        i = int(obj)  # Push a number onto the stack
        return True
    except:
        pass
    return False


def paramsConsumer(tokens, n):
    args = {}
    assert tokens[n] == "("
    n += 1
    count = 0
    while tokens[n] != ")":
        args[tokens[n]] = Param(tokens[n])  # store by name
        args[count] = tokens[n]  # store by order
        n += 1
        count += 1
        if tokens[n] == ",":
            n += 1
    n += 1
    return (n, args)


def argsConsumer(tokens, n, validSymbols):
    args = []
    arg = []
    assert tokens[n] == "("
    n += 1
    while tokens[n] != ")":
        if isInt(tokens[n]):
            arg.append(tokens[n])
            n += 1
        elif str(tokens[n])[0] == '$':
            arg.append(TemplateParam(tokens[n]))
            n += 1
        elif str(tokens[n])[0] == '"':  # Push data onto the stack
            arg.append(tokens[n])
            n += 1
        elif tokens[n] in validSymbols:
            (n, obj) = validSymbols[str(tokens[n])].parse(tokens, n + 1, validSymbols)
            arg.append(obj)
        else:
            if str(tokens[n]) == ")":
                continue
            # pdb.set_trace()
            raise Exception("invalid symbol: %s" % tokens[n])
        if str(tokens[n]) == ",":
            if len(arg) > 1:
                args.append(arg)
            else:
                args.extend(arg)
            arg = []
            n += 1
    if len(arg) > 1:
        args.append(arg)
    else:
        args.extend(arg)
    n += 1
    return (n, args)


class Binding:
    """Connects a macro definition with the arguments of a particular invocation
    """

    def __init__(self, name, parserFn=None):
        self.name = name
        self.invocation = None
        self.outputs = None
        self.parserFn = parserFn
        self.instanceOf = None

    def matchArgs(self, bindings):
        """Match passed arguments with their definitions to produce a dictionary of { symbol: binding } pairs.
           Since this is itself a binding, apply both this binding & the outer binding to the definition to create the final
           argument binding
        """
        if self.invocation:
            invocation = copy.copy(self.invocation)
        else:
            invocation = {}
        if bindings:
            invocation += bindings
        return self.instanceOf.matchArgs(invocation)

    def compile(self, symbols=None):
        """Compile into a list of statements, given an input substitution (symbol) table"""
        if self.instanceOf is None:               # name has no binding,
            self.instanceOf = symbols[self.name]  # so find it
        if symbols:
            syms = copy.copy(symbols)
        else:
            syms = {}
        cinv = compileParamsList(self.invocation, symbols)  # Compile all the args
        syms.update(self.instanceOf.matchArgs(cinv))
        ret = self.instanceOf.compile(syms)
        return ret

    def parse(self, tokens, n, symbols=None):
        """
        could be a basic variable or an invocation
        """
        if self.parserFn:
            return self.parserFn(self, tokens, n, symbols)
        else:
            params = None
            if tokens[n] == "(":
                params = []
                (n, p) = argsConsumer(tokens, n, symbols)
                params += p
            if n < len(tokens) and tokens[n] == "->":
                n += 1
                (n, p) = paramsConsumer(tokens, n)
                self.outputs = p
            self.invocation = params
            return (n, copy.copy(self))

class SpendScriptItem:
    def __init__(self, name, val):
        self.name = name
        if type(val) is str:
            self.val = val.strip("'").strip('"')
        else:
            self.val = val
        self.pushedOntoSatisfier = False

    def serialize(self):
        if not self.val is None:
            if type(self.val) is str:
                return bytes(self.val)
            else:
                return self.val
        else: # If this item isn't bound should I throw or return its unbound name?
            # raise err.Output("Spend script item has no value")
            return self.scriptify()

    def scriptify(self):
        return "@" + self.name

    def __repr__(self):
        return "<SpendScriptItem %s>" % self.name


class ResultData:
    def __init__(self, pushNum, opcode, args, altArgs):
        self.pushNum = pushNum
        self.opcode = opcode
        self.args = args # portion of the main stack that this opcode uses
        self.altArgs = altArgs # portion of the alt stack that this opcode uses

class Param:
    """
    """

    def __init__(self, name, parserFn=None):
        self.name = name

    def compile(self, symbols=None):
        # print(self.name[0])
        if self.name[0] == "@":  # This is an implicitly pushed stack parameter
            return [SpendScriptItem(self.name[1:], symbols.get(self.name, None))]  # return the binding if it exists or the param name
        if self.name[0] == "$":  # This is an implicitly pushed stack parameter
            pdb.set_trace()
            return [TemplateParam(self.name[1:], symbols.get(self.name, None))]  # return the binding if it exists or the param name
        binding = symbols.get(self.name)
        if binding is None:
            assert not "parameter %s is not bound" % self.name
        if type(binding) is list:  # Already compiled
            return binding
        if isinstance(binding,str):   # primitive
            return [binding]
        elif type(binding) is int:  # primitive
            return [binding]
        elif type(binding) is bytes:  # primitive
            return [binding]
        return binding.compile(symbols)  # compile it

    def parse(self, tokens, n, symbols=None):
        """
        could be a basic variable use or an invocation, used in the body of the function
        """
        if 1:
            params = None
            if tokens[n] == "(":
                params = []
                (n, p) = argsConsumer(tokens, n, symbols)
                params += p
            if n < len(tokens) and tokens[n] == "->":
                n += 1
                (n, p) = paramsConsumer(tokens, n)
                self.outputs = p
            self.invocation = params
            return (n, copy.copy(self))


class Primitive:
    def __init__(self, name, bin, stackConsumption, stackProduction, simFn, parserFn=None):
        self.name = name
        self.parserFn = parserFn
        self.outputs = None
        self.bin = bin
        self.stackConsumption = stackConsumption
        self.stackProduction = stackProduction
        self.simFn = simFn
        self.params = []

    def str(self):
        return self.name

    def __repr__(self):
        return "<Primitive %s>" % self.name

    def serialize(self):
        return bytes([self.bin])

    def compile(self, symbols):
        if self.params:
            ret = compileParamsList(self.params, symbols)
        else:
            ret = []

        ret.append(self)
        return ret

    def stackEffect(self, stack, altstack):
        """Returns ((consumed, produced), (altConsumed, altProduced)), which describes how this operation affects the stacks.  Does not modify stack or altstack"""
        ## TODO handle many weird cases
        return ((self.stackConsumption, self.stackProduction), (0,0))

    def parse(self, tokens, n, symbols=None):
        """
        default doesn't accept any other tokens
        """
        if self.parserFn:
            return self.parserFn(self, tokens, n, symbols)
        else:
            if tokens[n] == "(":  # invocation with params is optional
                (n, self.params) = argsConsumer(tokens, n, symbols)
            if tokens[n] == "->":
                (n, self.outputs) = paramsConsumer(tokens, n + 1)
            dup = copy.copy(self)
            return (n, dup)

def isPrimitive(obj, opcode):
    """Returns true if this is a primitive object of the passed opcode, or a string of that opcode (DON'T prefix with OP_)"""
    if type(obj) is Primitive:
        s = obj.name
    else:
        s = obj # Its a string
    return (s == opocde) or ("OP_" + opcode == s)

def isOpcode(obj, opcode):
    """Returns true if this any form of the passed opcode (DON'T prefix with OP_) string (object or string)"""
    if type(obj) is IfConstruct: s = "IF"
    elif type(obj) is ElseConstruct: s = "ELSE"
    elif type(obj) is Primitive:
        s = obj.name
    else:
        s = obj # Its a string
    return (s == opcode) or (s == "OP_" + opcode)


class RepeatConstruct:
    """Implement the repeat (n) {} construct"""

    def __init__(self):
        self.name = "repeat"
        self.statements = None
        self.arg = None
        self.outputs = None

    def parse(self, tokens, n, symbols=None):
        if tokens[n] == "(":  # optional if param
            (n, self.arg) = argsConsumer(tokens, n, symbols)
        if tokens[n] == "{":
            (n, self.statements) = statementConsumerCallout(tokens, n + 1, symbols)
        else:
            assert 0, "need block"
        assert tokens[n] == "}"
        return (n + 1, copy.copy(self))

    def compile(self, symbols):
        ret = []
        if not self.arg is None:
            assert len(self.arg) == 1, "if statement can only have one argument"

        repeatCount = int(self.arg[0])
        if not self.statements is None:
            stmts = compileStatementList(self.statements, symbols)
            for i in range(repeatCount):
                ret.extend(stmts)
        return ret

    def str(self):
        return self.name

    def serialize(self):
        assert(0)  # should never call this because compile causes this to disappear


class IfConstruct(Primitive):
    """Implement the if () {} construct"""

    def __init__(self):
        Primitive.__init__(self, "OP_IF", bchopcodes.opcode2bin("OP_IF"), 1, 0, simFn=None, parserFn=None)
        self.statements = None
        self.arg = None
        self.outputs = None

    def parse(self, tokens, n, symbols=None):
        if tokens[n] == "(":  # optional if param
            (n, self.arg) = argsConsumer(tokens, n, symbols)
        if tokens[n] == "{":
            (n, self.statements) = statementConsumerCallout(tokens, n + 1, symbols)
        else:
            assert 0, "need block"
        assert tokens[n] == "}"
        return (n + 1, copy.copy(self))

    def compile(self, symbols):
        ret = []
        if not self.arg is None:
            assert len(self.arg) == 1, "if statement can only have one argument"
            ret.extend(compileParamsList(self.arg, symbols))

        ret.append(self)
        if not self.statements is None:
            ret.extend(compileStatementList(self.statements, symbols))
        # TODO what if no else follows?
        return ret

    def str(self):
        return self.name[3:]

    def repr(self):
        return "<IfConstruct>"

    def serialize(self):
        return bytes([bchopcodes.opcode2bin(self.name)])



class ElseConstruct:
    """Implement the if () {} construct"""

    def __init__(self):
        self.name = "OP_ELSE"
        self.statements = None
        self.arg = None
        self.outputs = None

    def parse(self, tokens, n, symbols=None):
        if tokens[n] == "(":  # optional if param
            (m, self.arg) = argsConsumer(tokens, n, symbols)
        if tokens[n] == "{":
            (m, self.statements) = statementConsumerCallout(tokens, n + 1, symbols)
        else:
            assert 0, "need block"
        if tokens[m] != "}":
            raise err.Parse(reportBadStatement(tokens, m, symbols, False))

        # assert tokens[m] == "}"
        return (m + 1, copy.copy(self))

    def compile(self, symbols):
        ret = []
        if not self.arg is None:
            assert len(self.arg) == 0, "else statement cannot have arguments"
        ret.append(self)
        if not self.statements is None:
            ret.extend(compileStatementList(self.statements, symbols))
        ret.append(primitives["ENDIF"])
        return ret

    def str(self):
        return self.name[3:]

    def repr(self):
        return "<ElseConstruct>"

    def serialize(self):
        return bytes([bchopcodes.opcode2bin(self.name)])


def elseParser(prim, tokens, n, symbols):
    if tokens[n] == "{":
        (n, prim.statements) = statementConsumerCallout(tokens, n + 1, symbols)
    else:
        assert 0, "need block"
    assert tokens[n] == "}"
    return (n + 1, prim)


def repeatParser(prim, tokens, n, symbols):
    if tokens[n] == "(":
        (n, prim.arg) = argsConsumer(tokens, n, symbols)
    else:
        assert 0, "need args"
    if tokens[n] == "{":
        (n, prim.statements) = statementConsumerCallout(tokens, n + 1, symbols)
    else:
        assert 0, "need block"
    assert tokens[n] == "}"
    return (n + 1, prim)


SP_IF = IfConstruct()
SP_ELSE = ElseConstruct()  # Primitive("else", None, elseParser)
SP_REPEAT = RepeatConstruct()

def simExec(stk):
    # if these are constants pushed to the stack, we can still reason about them
    numReturns = stk[-1]
    numParams = stk[-2] + 3  # + 3 because these 2 stack items and the code
    return(numParams, numReturns)

SP_EXEC = Primitive("exec", None, None, simExec, None)

primitives = {
    "if": SP_IF,
    "else": SP_ELSE,
    "exec": SP_EXEC,
    "repeat": SP_REPEAT
}

for name, data in bchopcodes.opcodeData.items():
    if name[0:3] == "OP_": # add the opcodes without the OP_ prefix
        primitives[name] = Primitive(name[3:], data[0], data[1], data[2], data[3])
        try:
            i = int(name[3:])
            # If its a numerical constant opcode don't add it in its non OP_ form
        except:
            primitives[name[3:]] = Primitive(name[3:], data[0], data[1], data[2], data[3])
    else:
        primitives[name] = Primitive(name, data[0], data[1], data[2], data[3])

