#!/usr/bin/env python3

# library imports
import argparse
import logging
import sys
import argparse
import pathlib

# third party imports
import arrow
import attr
import requests
import logging_tree


__version__ = "1.0.0"
USER_AGENT_STRING = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0"

@attr.s(auto_attribs=True)
class UrlRequest:
    method:str = attr.ib()
    url:str = attr.ib()
    query:str = attr.ib(default=None)
    body:dict = attr.ib(default=None)
    headers:dict = attr.ib(default=None)
    response:requests.Response = attr.ib(default=None) # gets set after the request is processed

class Application:
    '''main application class
    '''

    def __init__(self, logger:logging.Logger, args:argparse.Namespace):
        ''' constructor
        @param logger the Logger instance
        @param args - the namespace object we get from argparse.parse_args()
        '''

        self.logger = logger
        self.args = args

        self.rsession = requests.session()

        self.rsession.headers.update({'User-Agent': USER_AGENT_STRING})


    def make_requests_call(self, request_to_make:UrlRequest) -> UrlRequest:

        result = None
        try:
            self.logger.debug("http request: %s - %s", request_to_make.method, request_to_make.url)
            result = self.rsession.request(
                method=request_to_make.method,
                url=request_to_make.url,
                headers=request_to_make.headers,
                params=request_to_make.query,
                data=request_to_make.body)


        except requests.RequestException as e:
            self.logger.exception(f"Error processing request: `{request_to_make}`")
            raise e

        self.logger.debug("http request: %s - %s -> %s", request_to_make.method, request_to_make.url, result.status_code)

        if result.status_code != 200:
            raise Exception(f"Request returned non 200 status code `{result.status_code}` with the request `{request_to_make}`")

        return attr.evolve(request_to_make, response=result)

    def run(self):

        common_headers = {"Host": "leetcode.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
             # their server supports 'brotli' so if you put 'br' in here you get back binary
             # instead of JSON text
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": "https://leetcode.com/",
            "Upgrade-Insecure-Requests": "1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "TE": "Trailers"}

        # hit the home page
        home_page_req = self.make_requests_call(UrlRequest(method="GET", url="https://leetcode.com"))

        csrf_token_from_cookie = home_page_req.response.cookies["csrftoken"]

        self.logger.debug("csrf middleware token from homepage request is `%s`", csrf_token_from_cookie)

        login_body_dict = {"login": self.args.username,
            "password": self.args.password,
            "next": "/problems",
            "csrfmiddlewaretoken": csrf_token_from_cookie }

        login_page_req = self.make_requests_call(
            UrlRequest(method="POST", url="https://leetcode.com/accounts/login", body=login_body_dict, headers=common_headers))

        self.logger.debug("login page req: `%s`", login_page_req)


        problems_set_all_req = self.make_requests_call(UrlRequest(method="GET", url="https://leetcode.com/api/problems/all",
         headers=common_headers))

        import pdb; pdb.set_trace()
        self.logger.debug("problem set all req: `%s`", problems_set_all_req)

        self.logger.debug("text: `%s`", problems_set_all_req.response.text)


class ArrowLoggingFormatter(logging.Formatter):
    ''' logging.Formatter subclass that uses arrow, that formats the timestamp
    to the local timezone (but its in ISO format)
    '''

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

if __name__ == "__main__":
    # if we are being run as a real program

    parser = argparse.ArgumentParser(
        description="downloads each problem from leetcode into individual files",
        epilog="Copyright 2019-09-10 Mark Grandi",
        fromfile_prefix_chars='@')

    # set up logging stuff
    logging.captureWarnings(True) # capture warnings with the logging infrastructure
    root_logger = logging.getLogger()
    logging_formatter = ArrowLoggingFormatter("%(asctime)s %(threadName)-10s %(name)-20s %(levelname)-8s: %(message)s")
    logging_handler = logging.StreamHandler(sys.stdout)
    logging_handler.setFormatter(logging_formatter)
    root_logger.addHandler(logging_handler)


    # silence urllib3 (requests) logger because its noisy
    requests_packages_urllib_logger = logging.getLogger("requests.packages.urllib3")
    requests_packages_urllib_logger.setLevel("INFO")
    urllib_logger = logging.getLogger("urllib3")
    urllib_logger.setLevel("INFO")

    parser.add_argument("username", type=str, help="leetcode username")
    parser.add_argument("password", type=str, help="leetcode password")
    parser.add_argument("path_to_save_to", metavar="path-to-save-to",
        type=isDirectoryType, help="the path to download the problems to")
    parser.add_argument("--version", action="version", help="show the program version", version=__version__)
    parser.add_argument("--verbose", action="store_true", help="Increase logging verbosity")



    try:
        parsed_args = parser.parse_args()

        # set logging level based on arguments
        if parsed_args.verbose:
            root_logger.setLevel("DEBUG")
        else:
            root_logger.setLevel("INFO")

        root_logger.debug("Parsed arguments: %s", parsed_args)
        root_logger.debug("Logger hierarchy:\n%s", logging_tree.format.build_description(node=None))


        # run the application
        app = Application(root_logger.getChild("app"), parsed_args)
        app.run()

        root_logger.info("Done!")
    except Exception as e:
        root_logger.exception("Something went wrong!")
        sys.exit(1)