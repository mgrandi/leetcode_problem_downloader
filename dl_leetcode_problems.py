#!/usr/bin/env python3

# library imports
import argparse
import logging
import sys
import argparse
import pathlib
import typing
import json

# third party imports
import arrow
import attr
import requests
import logging_tree
import html2text
import jmespath


__version__ = "1.0.0"
USER_AGENT_STRING = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0"
JMESPATH_API_PROBLEMS_ALL_SEARCH_QUERY = jmespath.compile("stat_status_pairs")

JMESPATH_Q_QUESTION_ID = jmespath.compile("stat.question_id")
JMESPATH_Q_TITLE = jmespath.compile("stat.question__title")
JMESPATH_Q_SLUG = jmespath.compile("stat.question__title_slug")
JMESPATH_Q_DIFFICULTY = jmespath.compile("difficulty.level")
JMESPATH_Q_PAID_ONLY = jmespath.compile("paid_only")


GRAPHQL_QUESTIONDATA_QUERY = '''query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    boundTopicId
    title
    titleSlug
    content
    codeSnippets {
      lang
      langSlug
      code
      __typename
    }
  }
}

'''

COMMON_HEADERS = {"Host": "leetcode.com",
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


@attr.s(auto_attribs=True)
class UrlRequest:
    method:str = attr.ib()
    url:str = attr.ib()
    query:str = attr.ib(default=None) # optional
    body:dict = attr.ib(default=None) # optional
    body_is_json:bool = attr.ib(default=False)
    headers:dict = attr.ib(default=None) # optional
    response:requests.Response = attr.ib(default=None) # gets set after the request is processed

@attr.s(auto_attribs=True)
class SingleLeetcodeProblemCodeSnippet:
    ''' represents the code snippet that gets filled in when
    you start the problem on the leetcode editor for a given language

    this information comes from the `graphql (questionData)` endpoint
    '''

    language:str = attr.ib()
    language_slug:str = attr.ib()
    code_snippet:str = attr.ib()


@attr.s(auto_attribs=True)
class SingleLeetcodeProblem:
    ''' represents a single problem from leetcode

    fields are a combination of information returned from the `/api/problems/all`
    and the `graphql (questionData)` endpoints

    '''

    question_id:int = attr.ib()
    title:str = attr.ib()
    slug:str = attr.ib()
    difficulty:int = attr.ib()
    paid_only:bool = attr.ib()
    question_content:str = attr.ib(default=None)
    code_snippets:typing.Mapping[str, SingleLeetcodeProblemCodeSnippet] = attr.ib(default=None)


@attr.s(auto_attribs=True)
class AllLeetcodeProblems:
    problems:typing.Mapping[int,SingleLeetcodeProblem] = attr.ib()


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

        self.text_converter = html2text.HTML2Text()
        self.text_converter.unicode_snob = True
        self.text_converter.mark_code = True


    def make_requests_call(self, request_to_make:UrlRequest) -> UrlRequest:

        result = None
        try:
            self.logger.debug("http request: %s - %s", request_to_make.method, request_to_make.url)

            actual_body = request_to_make.body

            # easier to just manually convert to json here rather than copying and pasting the session.request call
            # with a different body= or json= parameter
            if request_to_make.body_is_json:
                actual_body = json.dumps(request_to_make.body)
            result = self.rsession.request(
                method=request_to_make.method,
                url=request_to_make.url,
                headers=request_to_make.headers,
                params=request_to_make.query,
                data=actual_body)


        except requests.RequestException as e:
            self.logger.exception(f"Error processing request: `{request_to_make}`")
            raise e

        self.logger.debug("http request: %s - %s -> %s", request_to_make.method, request_to_make.url, result.status_code)

        if result.status_code != 200:
            raise Exception(f"Request returned non 200 status code `{result.status_code}` with the request `{request_to_make}`, and cookies: `{self.rsession.cookies}`, and text: `{result.text}`, raw: `{result.request.body}`")

        return attr.evolve(request_to_make, response=result)

    def jmespath_search_helper(self, jmespath_compiled_query, dict_to_search, description):
        '''
        helper that runs a jmespath search and raises an exception if we get None back

        @param dict_to_search the dictionary to search using .search()
        @param jmespath_compiled_query the query object to call search on
        @param description a string that gets inserted into the log message
        @return the result of the .search() call or throws an exception
        '''

        self.logger.debug("using jmespath compiled query `%s` to search, description: `%s`",
         jmespath_compiled_query, description)

        jmespath_search_result = jmespath_compiled_query.search(dict_to_search)

        self.logger.debug("jmespath compiled query `%s` returned an object of type `%s`",
            JMESPATH_API_PROBLEMS_ALL_SEARCH_QUERY, type(jmespath_search_result))

        if jmespath_search_result == None:
            raise Exception(
                f"jmespath compiled search `{jmespath_compiled_query}` (`{description}`) returned None")

        return jmespath_search_result


    def parse_api_problems_all_response(self, response_dict:dict) -> AllLeetcodeProblems:
        '''
        parses the response from leetcode.com/api/problems/all , which is the list of problems
        and some basic stuff about them, but not the actual probelms themselves

        @param response_dict the dictionary we get from the web request that contains the problems
        @return a AllLeetcodeProblems object
        '''

        result_dict = dict()

        try:

            problems_list_result = self.jmespath_search_helper(
                JMESPATH_API_PROBLEMS_ALL_SEARCH_QUERY, response_dict, "problems list")

            self.logger.info("have `%s` questions to parse", len(problems_list_result))

            # go through each question in the list (after sorting by question id) and then parse them into
            # a SingleLeetcodeProblem object
            for iter_problem_dict in sorted(problems_list_result, key=lambda x: JMESPATH_Q_QUESTION_ID.search(x)):

                single_q = SingleLeetcodeProblem(
                    question_id = self.jmespath_search_helper(JMESPATH_Q_QUESTION_ID, iter_problem_dict, "single question -> question_id"),
                    title = self.jmespath_search_helper(JMESPATH_Q_TITLE, iter_problem_dict, "single question -> title"),
                    slug = self.jmespath_search_helper(JMESPATH_Q_SLUG, iter_problem_dict, "single question -> slug"),
                    difficulty = self.jmespath_search_helper(JMESPATH_Q_DIFFICULTY, iter_problem_dict, "single question -> difficulty"),
                    paid_only = self.jmespath_search_helper(JMESPATH_Q_PAID_ONLY, iter_problem_dict, "single question -> paid only"),
                    question_content = None,
                    code_snippets = None)

                result_dict[single_q.question_id] = single_q
                self.logger.info("Question `%s` - `%s` parsed successfully", single_q.question_id, single_q.title)


        except Exception as e:
            self.logger.exception("Problem when parsing the /api/problems/all api response")
            raise e

        self.logger.info("`%s` questions parsed successfully", len(problems_list_result))
        return AllLeetcodeProblems(problems=result_dict)


    def make_homepage_request(self) -> UrlRequest:
        '''
        makes the http request for the leetcode homepage

        @return the resulting UrlRequest
        '''

        # hit the home page
        home_page_response_req = self.make_requests_call(UrlRequest(method="GET", url="https://leetcode.com"))

        return home_page_response_req


    def get_csrf_token_from_cookiejar(self) -> str:
        '''
        returns the CSRF token from the cookie jar
        @return the CSRF token as a string
        '''

        csrf_token_from_cookie = self.rsession.cookies["csrftoken"]

        self.logger.debug("csrf middleware token from the cookie jar is `%s`", csrf_token_from_cookie)
        return csrf_token_from_cookie


    def make_login_page_request(self, csrf_token) -> UrlRequest:
        '''
        makes the HTTP request to login to leetcode

        @param csrf_token the CSRF token we got from the homepage request
        @return the resulting UrlRequest
        '''

        login_body_dict = {"login": self.args.username,
            "password": self.args.password,
            "next": "/problems",
            "csrfmiddlewaretoken": csrf_token }

        login_page_response_req = self.make_requests_call(
            UrlRequest(method="POST",
                url="https://leetcode.com/accounts/login",
                body=login_body_dict,
                headers=COMMON_HEADERS))

        return login_page_response_req

    def make_api_problems_all_request(self) -> UrlRequest:
        '''
        makes the HTTP request to hit the /api/problems/all API
        @return the resulting UrlRequest
        '''

        problems_set_all_req = self.make_requests_call(
            UrlRequest(method="GET", url="https://leetcode.com/api/problems/all",
         headers=COMMON_HEADERS))

        return problems_set_all_req


    def make_graphql_questiondata_query(self, csrf_token, leetcode_question:SingleLeetcodeProblem) -> UrlRequest:
        '''
        method to make a HTTP request to get the 'extended' information about a individual leetcode question

        @param leetcode_question the SingleLeetcodeProblem object that we want the extended info for
        @param csrf_token the CSRF token we got from the home page request
        @return the resulting UrlRequest
        '''

        question_data_body_dict = {
            "operationName": "questionData",
            "variables": {
                "titleSlug": leetcode_question.slug
            },
            "query": GRAPHQL_QUESTIONDATA_QUERY
        }

        headers = COMMON_HEADERS.copy()

        headers["x-csrftoken"] = csrf_token
        headers["Content-Type"] = "application/json"
        headers["Referer"] = f"https://leetcode.com/problems/{leetcode_question.slug}"

        graphql_req = UrlRequest(
            method="POST",
            url="https://leetcode.com/graphql",
            body=question_data_body_dict,
            body_is_json=True,
            headers=headers)

        graphql_response_req = self.make_requests_call(graphql_req)

        return graphql_response_req


    def update_leetcode_problems_with_content_and_snippets(self, csrf_token, all_problems:AllLeetcodeProblems) -> AllLeetcodeProblems:
        '''
        goes through all of our leetcode problems and update the SingleLeetcodeProblem instances
        with the question content and the code snippet information

        @param all_problems the AllLeetcodeProblems instance we have
        @param csrf_token the CSRF token we got from the homepage request
        @return an updated AllLeetcodeProblems instance with the members having the question content
            and code snippets updated
        '''

        # not good form to modify the dict while iterating over it so lets just create
        # a new dict to insert the updated entries into
        result_dict = dict()

        for question_idx, iter_single_lc_question in all_problems.problems.items():


            self.logger.info("Updating Question `%s` - `%s`", question_idx, iter_single_lc_question.title)

            graphql_response_req = self.make_graphql_questiondata_query(csrf_token, iter_single_lc_question)




    def run(self):



        home_page_urlrequest = self.make_homepage_request()

        csrf_token_from_cookie = self.get_csrf_token_from_cookiejar()

        login_page_urlrequest = self.make_login_page_request(csrf_token_from_cookie)

        # logging in updates the csrf token
        csrf_token_from_cookie = self.get_csrf_token_from_cookiejar()


        problem_set_all_urlrequest = self.make_api_problems_all_request()

        all_leetcode_problems = self.parse_api_problems_all_response(problem_set_all_urlrequest.response.json())

        all_leetcode_problems = self.update_leetcode_problems_with_content_and_snippets(
            csrf_token_from_cookie, all_leetcode_problems)



        # import pprint
        # self.logger.debug("questions: `%s`", pprint.pformat(all_leetcode_problems.problems))

        # import pdb; pdb.set_trace()
        # self.logger.debug("problem set all req: `%s`", problems_set_all_req)

        # self.logger.debug("text: `%s`", problems_set_all_req.response.text)


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