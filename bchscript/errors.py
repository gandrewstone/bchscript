

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class Parse(Error):
    """ Error parsing the program"""
    pass

class Output(Error):
    """ Error parsing the program"""
    pass

class Symbol(Error):
    """ Error parsing the program"""
    pass
