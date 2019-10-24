import argparse
import pathlib
import logging
import pathlib

import arrow

class ArrowLoggingFormatter(logging.Formatter):
    ''' logging.Formatter subclass that uses arrow, that formats the timestamp
    to the local timezone (but its in ISO format)
    '''

    def __init__(self, fmt, dateFmt=None, style='%'):
        super().__init__(fmt, dateFmt)

    def formatTime(self, record, datefmt=None):
        # use the 'timestamp' format code
        return arrow.get(f"{record.created}", "X").to("local").isoformat()

def isDirectoryType(stringArg):
    ''' helper method for argparse to see if the argument is a directory
    @param stringArg - the argument we get from argparse
    @return the path if it is indeed a directory, or raises ArgumentTypeError if its not.'''

    path = None
    try:
        path = pathlib.Path(stringArg).resolve()
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Problem parsing `{stringArg}` as a path! Exception: `{e}`")

    if not path.is_dir() or not path.exists():
        raise argparse.ArgumentTypeError(f"{stringArg} is not a directory or doesn't exist!")

    return path

def isFileType(filePath):
    ''' see if the file path given to us by argparse is a file
    @param filePath - the filepath we get from argparse
    @return the filepath as a pathlib.Path() if it is a file, else we raise a ArgumentTypeError'''

    path_maybe = pathlib.Path(filePath)
    path_resolved = None

    # try and resolve the path
    try:
        path_resolved = path_maybe.resolve(strict=True)

    except Exception as e:
        raise argparse.ArgumentTypeError("Failed to parse `{}` as a path: `{}`".format(filePath, e))

    # double check to see if its a file
    if not path_resolved.is_file():
        raise argparse.ArgumentTypeError("The path `{}` is not a file!".format(path_resolved))

    return path_resolved