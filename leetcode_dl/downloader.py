import sys
import argparse
import pathlib
import typing
import time
import logging
import json

# third party imports
import arrow
import attr
import requests
import logging_tree
import html2text
import jmespath

from leetcode_dl.model import SingleLeetcodeProblemCodeSnippet, SingleLeetcodeProblem, AllLeetcodeProblems, UrlRequest
from leetcode_dl import constants


logger = logging.getLogger(__name__)
jmespath_logger = logger.getChild("jmespath")

class LeetcodeProblemDownloader:
    '''main application class
    '''

    def __init__(self, args:argparse.Namespace):
        ''' constructor
        @param logger the Logger instance
        @param args - the namespace object we get from argparse.parse_args()
        '''

        self.logger = logger
        self.args = args

        self.rsession = requests.session()

        self.rsession.headers.update({'User-Agent': constants.USER_AGENT_STRING})

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

        jmespath_logger.debug("using jmespath compiled query `%s` to search, description: `%s`",
         jmespath_compiled_query, description)

        jmespath_search_result = jmespath_compiled_query.search(dict_to_search)

        jmespath_logger.debug("jmespath compiled query `%s` returned an object of type `%s`",
            constants.JMESPATH_API_PROBLEMS_ALL_SEARCH_QUERY, type(jmespath_search_result))

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
                constants.JMESPATH_API_PROBLEMS_ALL_SEARCH_QUERY, response_dict, "problems list")

            self.logger.info("have `%s` questions to parse", len(problems_list_result))

            # go through each question in the list (after sorting by question id) and then parse them into
            # a SingleLeetcodeProblem object
            for iter_problem_dict in sorted(problems_list_result, key=lambda x: constants.JMESPATH_Q_QUESTION_ID.search(x)):

                single_q = SingleLeetcodeProblem(
                    question_id = self.jmespath_search_helper(constants.JMESPATH_Q_QUESTION_ID, iter_problem_dict,
                        "single question -> question_id"),
                    title = self.jmespath_search_helper(constants.JMESPATH_Q_TITLE, iter_problem_dict,
                        "single question -> title"),
                    slug = self.jmespath_search_helper(constants.JMESPATH_Q_SLUG, iter_problem_dict,
                        "single question -> slug"),
                    difficulty = self.jmespath_search_helper(constants.JMESPATH_Q_DIFFICULTY, iter_problem_dict,
                        "single question -> difficulty"),
                    paid_only = self.jmespath_search_helper(constants.JMESPATH_Q_PAID_ONLY, iter_problem_dict,
                        "single question -> paid only"),
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
                headers=constants.COMMON_HEADERS))

        return login_page_response_req

    def make_api_problems_all_request(self) -> UrlRequest:
        '''
        makes the HTTP request to hit the /api/problems/all API
        @return the resulting UrlRequest
        '''

        problems_set_all_req = self.make_requests_call(
            UrlRequest(method="GET", url="https://leetcode.com/api/problems/all",
         headers=constants.COMMON_HEADERS))

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
            "query": constants.GRAPHQL_QUESTIONDATA_QUERY
        }

        # don't modify the constant value
        headers = constants.COMMON_HEADERS.copy()

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

            res_json_dict = graphql_response_req.response.json()

            question_html = self.jmespath_search_helper(constants.JMESPATH_Q_CONTENT, res_json_dict,
                "question data -> content")
            question_as_markdown = self.text_converter.handle(question_html)
            question_code_snippets = self.jmespath_search_helper(constants.JMESPATH_Q_CODE_SNIPPETS, res_json_dict,
                "question data -> code snippets")

            self.logger.debug("have `%s` snippets to process for Question `%s` - `%s`",
                len(question_code_snippets), question_idx, iter_single_lc_question.title)

            code_snippet_dict = dict()

            for iter_code_snippet_dict in question_code_snippets:

                code_snippet_obj = SingleLeetcodeProblemCodeSnippet(
                    language = self.jmespath_search_helper(constants.JMESPATH_Q_CODE_SNIPPET_LANGUAGE,
                        iter_code_snippet_dict, "question data -> code snippet -> language"),
                    language_slug = self.jmespath_search_helper(constants.JMESPATH_Q_CODE_SNIPPET_LANGUAGE_SLUG,
                        iter_code_snippet_dict, "question data -> code snippet -> language slug"),
                    code_snippet = self.jmespath_search_helper(constants.JMESPATH_Q_CODE_SNIPPET_CONTENT,
                        iter_code_snippet_dict, "question data -> code snippet -> code"))

                self.logger.debug("new code snippet obj for Question `%s` - `%s`: `%s`",
                    question_idx, iter_single_lc_question.title, code_snippet_obj)

                code_snippet_dict[code_snippet_obj.language_slug] = code_snippet_obj

            # now evolve the SingleLeetcodeProblem and put it in the new dict
            new_single_lc_problem = attr.evolve(iter_single_lc_question,
                question_content=question_as_markdown,
                code_snippets=code_snippet_dict)

            result_dict[new_single_lc_problem.question_id] = new_single_lc_problem

            self.logger.debug("sleeping for `%s` seconds...", constants.SECONDS_TO_SLEEP_BETWEEN_GRAPHQL_API_REQUESTS)
            time.sleep(constants.SECONDS_TO_SLEEP_BETWEEN_GRAPHQL_API_REQUESTS)


        return AllLeetcodeProblems(problems=result_dict)


    def get_all_leetcode_problems(self) -> AllLeetcodeProblems:


        home_page_urlrequest = self.make_homepage_request()

        csrf_token_from_cookie = self.get_csrf_token_from_cookiejar()

        login_page_urlrequest = self.make_login_page_request(csrf_token_from_cookie)

        # logging in updates the csrf token
        csrf_token_from_cookie = self.get_csrf_token_from_cookiejar()

        problem_set_all_urlrequest = self.make_api_problems_all_request()

        # get the problems without the question content and the code snippets
        all_leetcode_problems = self.parse_api_problems_all_response(problem_set_all_urlrequest.response.json())

        # update the problems with the question content and the code snippets
        all_leetcode_problems = self.update_leetcode_problems_with_content_and_snippets(
            csrf_token_from_cookie, all_leetcode_problems)

        return all_leetcode_problems