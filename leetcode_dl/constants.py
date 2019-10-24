import leetcode_dl.model as model

import jmespath

SECONDS_TO_SLEEP_BETWEEN_GRAPHQL_API_REQUESTS = 2

USER_AGENT_STRING = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0"

# jmespath expresson for getting out the question list in the api/problems/all API
JMESPATH_API_PROBLEMS_ALL_SEARCH_QUERY = jmespath.compile("stat_status_pairs")

# jmespath expression for getting various parts of data out in the response from
# the graphql questionData API
JMESPATH_Q_QUESTION_ID = jmespath.compile("stat.question_id")
JMESPATH_Q_TITLE = jmespath.compile("stat.question__title")
JMESPATH_Q_SLUG = jmespath.compile("stat.question__title_slug")
JMESPATH_Q_DIFFICULTY = jmespath.compile("difficulty.level")
JMESPATH_Q_PAID_ONLY = jmespath.compile("paid_only")

JMESPATH_Q_CONTENT = jmespath.compile("data.question.content")
JMESPATH_Q_CODE_SNIPPETS = jmespath.compile("data.question.codeSnippets")

JMESPATH_Q_CODE_SNIPPET_LANGUAGE = jmespath.compile("lang")
JMESPATH_Q_CODE_SNIPPET_LANGUAGE_SLUG = jmespath.compile("langSlug")
JMESPATH_Q_CODE_SNIPPET_CONTENT = jmespath.compile("code")

# if you have the JSON for a "graphql questionData" response, you can figure out
# what code snippets for each language are by using this `jq` query:
#
# jq ".data.question.codeSnippets[] | {language:.lang, language_slug:.langSlug}" "<JSON FILE>"
KNOWN_LANGUAGE_SLUG_TO_FILE_EXT_DICT = {
    "cpp": model.ProgrammingLanguageMetadata(file_ext="cpp", comment_characters="//"),
    "java": model.ProgrammingLanguageMetadata(file_ext="java", comment_characters="//"),
    "python": model.ProgrammingLanguageMetadata(file_ext="py", comment_characters="#"),
    "python3": model.ProgrammingLanguageMetadata(file_ext="py", comment_characters="#"),
    "c": model.ProgrammingLanguageMetadata(file_ext="c", comment_characters="//"),
    "csharp": model.ProgrammingLanguageMetadata(file_ext="cs", comment_characters="//"),
    "javascript": model.ProgrammingLanguageMetadata(file_ext="js", comment_characters="//"),
    "ruby": model.ProgrammingLanguageMetadata(file_ext="rb", comment_characters="#"),
    "swift": model.ProgrammingLanguageMetadata(file_ext="swift", comment_characters="//"),
    "go": model.ProgrammingLanguageMetadata(file_ext="go", comment_characters="//"),
    "scala": model.ProgrammingLanguageMetadata(file_ext="scala", comment_characters="//"),
    "kotlin": model.ProgrammingLanguageMetadata(file_ext="kt", comment_characters="//"),
    "php": model.ProgrammingLanguageMetadata(file_ext="php", comment_characters="//"),
}

DEFAULT_FILE_EXTENSION = ".txt"
DEFAULT_COMMENT_CHARACTERS = "//"

PROGRAMMING_LANGUAGE_CHOICE_ALL = "ALL"

# the query (as a string!) that we make to the graphql questionData API
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

# common headers for making requests to leetcode
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

