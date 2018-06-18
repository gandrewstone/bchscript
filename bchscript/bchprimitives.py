import pdb
import copy
import bchscript.bchopcodes as bchopcodes

statementConsumerCallout = None


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
        else:
            temp = s.compile(symbols)
            if type(temp) == list:
                ret.extend(temp)
            else:
                ret.append(temp)
    return ret


def isInt(obj):
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
            arg.append(int(tokens[n]))
            n += 1
        elif tokens[n][0] == '"':  # Push data onto the stack
            arg.append(tokens[n])
            n += 1
        elif tokens[n] in validSymbols:
            (n, obj) = validSymbols[tokens[n]].parse(tokens, n + 1, validSymbols)
            arg.append(obj)
        else:
            if tokens[n] == ")":
                continue
            pdb.set_trace()
            raise Exception("invalid symbol: %s" % tokens[n])
        if tokens[n] == ",":
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
        self.val = val.strip("'").strip('"')

    def serialize(self):
        pdb.set_trace()

    

class Param:
    """
    """

    def __init__(self, name, parserFn=None):
        self.name = name

    def compile(self, symbols=None):
        if self.name[0] == "@":  # This is an implicitly pushed stack parameter
            return [SpendScriptItem(self.name, symbols.get(self.name, None))]  # return the binding if it exists or the param name
        binding = symbols.get(self.name)
        if binding is None:
            assert not "parameter %s is not bound" % self.name
        if type(binding) is list:  # Already compiled
            return binding
        if type(binding) is str:   # primitive
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
    def __init__(self, name, bin, parserFn=None):
        self.name = name
        self.parserFn = parserFn
        self.outputs = None
        self.bin = bin
        self.params = []

    def str(self):
        return self.name

    def serialize(self):
        return bytes([self.bin])

    def compile(self, symbols):
        if self.params:
            ret = compileParamsList(self.params, symbols)
        else:
            ret = []

        ret.append(self)
        return ret

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


class IfConstruct:
    """Implement the if () {} construct"""

    def __init__(self):
        self.name = "OP_IF"
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
        ret.append("OP_IF")
        if not self.statements is None:
            ret.extend(compileStatementList(self.statements, symbols))
        # TODO what if no else follows?
        return ret


class ElseConstruct:
    """Implement the if () {} construct"""

    def __init__(self):
        self.name = "OP_ELSE"
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
        ret.append("OP_ELSE")
        if not self.statements is None:
            ret.extend(compileStatementList(self.statements, symbols))
        ret.append("OP_ENDIF")
        return ret


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
SP_REPEAT = Primitive("repeat", None, repeatParser)

SP_EXEC = Primitive("exec", None)

primitives = {
    "if": SP_IF,
    "else": SP_ELSE,
    "exec": SP_EXEC,
    "repeat": SP_REPEAT
}

for name, bin in bchopcodes.opcode2bin.items():
    primitives[name] = Primitive(name, bin)
