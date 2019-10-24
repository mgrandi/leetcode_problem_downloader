import typing

import attr
import requests

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
