import jmespath

SECONDS_TO_SLEEP_BETWEEN_GRAPHQL_API_REQUESTS = 5

USER_AGENT_STRING = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0"

JMESPATH_API_PROBLEMS_ALL_SEARCH_QUERY = jmespath.compile("stat_status_pairs")

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

