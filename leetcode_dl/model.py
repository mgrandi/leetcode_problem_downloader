import typing
import logging

import attr
import requests

logger = logging.getLogger(__name__)

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
class ProgrammingLanguageMetadata:
    file_ext:str = attr.ib()
    comment_characters:str = attr.ib()

@attr.s(auto_attribs=True)
class SingleLeetcodeProblemCodeSnippet:
    ''' represents the code snippet that gets filled in when
    you start the problem on the leetcode editor for a given language

    this information comes from the `graphql (questionData)` endpoint
    '''

    language:str = attr.ib()
    language_slug:str = attr.ib()
    code_snippet:str = attr.ib()

    def get_code_snippet_file_extension(self) -> str:
        ''' returns the file extension that a source code file for the programming language
        that this code snippet represents should have

        @return the file extension without any periods at the start of the string, so `png` not `.png`
            if we don't recognize the programming language, we will return a default
        '''
        # have import here to not have circular dependency
        from leetcode_dl import constants


        if self.language_slug in constants.KNOWN_LANGUAGE_SLUG_TO_FILE_EXT_DICT.keys():
            return constants.KNOWN_LANGUAGE_SLUG_TO_FILE_EXT_DICT[self.language_slug].file_ext
        else:
            logger.warning("get_code_snippet_file_extension() called on a SingleLeetcodeProblemCodeSnippet whose" +
                "language_slug of `%s` is not in the known dictionary, returning `txt`", self.language_slug)
            return constants.DEFAULT_FILE_EXTENSION

    def get_code_snippet_comment_characters(self) -> str:
        ''' returns the character(s) that signify the start of a comment in the programming language
        that this object represents

        @return the character(s) that start a comment in the language this obj represents, returns a default if unknown
        '''
        # have import here to not have circular dependency
        from leetcode_dl import constants


        if self.language_slug in constants.KNOWN_LANGUAGE_SLUG_TO_FILE_EXT_DICT.keys():
            return constants.KNOWN_LANGUAGE_SLUG_TO_FILE_EXT_DICT[self.language_slug].comment_characters
        else:
            logger.warning("get_code_snippet_comment_characters() called on a SingleLeetcodeProblemCodeSnippet whose" +
                "language_slug of `%s` is not in the known dictionary, returning `//`", self.language_slug)
            return constants.DEFAULT_COMMENT_CHARACTERS

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

    def get_code_snippet(self, language_slug):
        ''' returns the SingleLeetcodeProblemCodeSnippet object for the given parameter
        @param language_slug the slug of the CodeSnippet object you want
        @return the CodeSnippet object, or None if it is not present
        '''

        if language_slug in self.code_snippets.keys():
            return self.code_snippets[language_slug]
        else:
            logger.warning("SingleLeetcodeProblem.get_code_snippet() called with a language slug of `%s`, "
                + "but we don't have a code snippet for that language", language_slug)
            return None


@attr.s(auto_attribs=True)
class AllLeetcodeProblems:
    problems:typing.Mapping[int,SingleLeetcodeProblem] = attr.ib()
