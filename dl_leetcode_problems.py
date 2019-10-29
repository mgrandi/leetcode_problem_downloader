#!/usr/bin/env python3

# library imports
import argparse
import logging
import logging.config
import json
import sys
import pathlib
import io

import arrow
import logging_tree

import leetcode_dl
from leetcode_dl import downloader
from leetcode_dl import utils
from leetcode_dl import constants
from leetcode_dl import model



def run(parsed_args, root_logger):


    logger = root_logger.getChild("main")
    app = downloader.LeetcodeProblemDownloader(parsed_args)
    all_leetcode_problems = app.get_all_leetcode_problems()

    programming_languages_to_use = []

    # see what languages we are considering. if ALL is present , just select all supported languages,
    # else, use what the user passed in
    if constants.PROGRAMMING_LANGUAGE_CHOICE_ALL in parsed_args.programming_languages:
        programming_languages_to_use = utils.get_choices_for_programming_language()
    else:
        programming_languages_to_use = parsed_args.programming_languages

    logger.info("Programming languages to write problems for: `%s`", programming_languages_to_use)

    logger.info("Writing problems to the folder: `%s`", parsed_args.path_to_save_to)

    # keep track of what problems we couldn't create a source code file for
    non_fatal_error_list = []

    # iterate through each problem
    for iter_question_idx, iter_single_lc_problem in all_leetcode_problems.problems.items():
        logger.debug("writing problem `%s` - `%s`", iter_single_lc_problem.question_id, iter_single_lc_problem.title)

        # the title's LOOK like they should be safe, might have to edit this if this turns out to not be the case
        problem_folder = parsed_args.path_to_save_to / f"{iter_single_lc_problem.question_id} - {iter_single_lc_problem.title}"

        logger.debug("-- creating problem folder: `%s`", problem_folder)

        problem_folder.mkdir(exist_ok=True)

        # now create a file for each programming language the user wants files for

        for iter_programming_lang_str in programming_languages_to_use:


            # now get the file that we will be writing to
            code_snippet_obj = iter_single_lc_problem.get_code_snippet(iter_programming_lang_str)

            logger.debug("---- language: `%s`, code_snippet_obj: `%s`",
                iter_programming_lang_str, code_snippet_obj)

            # NOTE: it seems that sometimes, leetcode doesn't have the 'complete' list of snippets for each problem
            # so if the user has requested a language but leetcode didn't give it to us, log a warning
            if code_snippet_obj == None:

                nfe = ErrorWhenWritingSourceCodeFile(
                    problem_obj=iter_single_lc_problem,
                    language_slug = iter_programming_lang_str,
                    reason=f"Leetcode did not give us a code snippet for the specified language, they only had `{iter_single_lc_problem.get_available_code_snippets}`")
                non_fatal_error_list.append(nfe)
                logger.warning("Problem writing source code file for problem `%s` - `%s`, reason: `%s`",
                     iter_single_lc_problem.question_id, iter_single_lc_problem.title, nfe.reason)
                continue

            file_name =  f"{iter_single_lc_problem.question_id}_{iter_single_lc_problem.slug}.{code_snippet_obj.get_code_snippet_file_extension()}"

            iter_problem_file = problem_folder / file_name

            logger.debug("------ file path: `%s`", iter_problem_file)

            if iter_problem_file.exists() and not parsed_args.overwrite:
                raise Exception(f"the file `{iter_problem_file}` already exists and --overwrite was not provided, not writing over an existing file")

            # open the file
            with open(iter_problem_file, "w", encoding="utf-8") as f:

                # write the problem questions in comments first
                question_io = io.StringIO(iter_single_lc_problem.question_content)
                logger.debug("------ question content: `%s`", iter_single_lc_problem.question_content.encode("utf-8"))

                while (iter_question_line := question_io.readline()):
                    str_to_write = f"{code_snippet_obj.get_code_snippet_comment_characters()} {iter_question_line}"

                    # the question content seems to have a mix of newlines and newlines + carriage returns, so
                    # get rid of the carriage returns. I think what is happening is python determines that it is
                    # `\n` newlines but since leetcode seems to be inconsistent , if i hae the carriage returns
                    # left in the string, i get gaps in the comments in the problem file which looks linda ugly
                    logger.debug("-------- before replacing \\r: `%s`", str_to_write.encode("utf-8"))
                    str_to_write = str_to_write.replace("\r", "")
                    logger.debug("-------- after replacing \\r:  `%s`", str_to_write.encode("utf-8"))
                    logger.debug("-------- writing: `%s`", str_to_write.encode("utf-8"))
                    f.write(str_to_write)

                # write a few spaces
                f.write("\n\n")

                # now write the code snippet
                f.write(code_snippet_obj.code_snippet)

            logger.debug("------ language `%s` done", iter_programming_lang_str)



if __name__ == "__main__":
    # if we are being run as a real program

    parser = argparse.ArgumentParser(
        description="downloads each problem from leetcode into individual files",
        epilog="Copyright 2019-09-10 Mark Grandi",
        fromfile_prefix_chars='@')

    # set up logging stuff
    logging.captureWarnings(True) # capture warnings with the logging infrastructure
    root_logger = logging.getLogger()
    logging_formatter = utils.ArrowLoggingFormatter("%(asctime)s %(threadName)-10s %(name)-10s %(levelname)-8s: %(message)s")
    logging_handler = logging.StreamHandler(sys.stdout)
    logging_handler.setFormatter(logging_formatter)
    root_logger.addHandler(logging_handler)

    parser.add_argument("--username", type=str, help="leetcode username")
    parser.add_argument("--password", type=str, help="leetcode password")
    parser.add_argument("--programming-languages", dest="programming_languages", type=str, nargs="+",
        choices=utils.get_choices_for_programming_language(),
        help="the programming languages to create problem files for, can specify multiple separated by a space. "
        + "Choose 'ALL' if you want files for every language")
    parser.add_argument("--path-to-save-to", dest="path_to_save_to",
        type=utils.isDirectoryType, help="the path to download the problems to")

    parser.add_argument("--overwrite", action="store_true", help="if provided, we will overwrite any existing files")

    parser.add_argument("--version", action="version", help="show the program version", version=leetcode_dl.__version__)

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--verbose", action="store_true", help="Increase logging verbosity")
    group.add_argument("--logging-config", dest="logging_config",
        type=utils.isFileType, help="Specify a JSON file representing logging configuration")

    try:
        parsed_args = parser.parse_args()

        # set logging level based on arguments
        if parsed_args.verbose:
            root_logger.setLevel("DEBUG")
        else:
            if parsed_args.logging_config:
                with open(parsed_args.logging_config, "r", encoding="utf-8") as f:
                    logging.config.dictConfig(json.load(f))
            else:
                root_logger.setLevel("INFO")

        root_logger.debug("Parsed arguments: %s", parsed_args)
        root_logger.debug("Logger hierarchy:\n%s", logging_tree.format.build_description(node=None))

        # run the application
        run(parsed_args, root_logger)

        root_logger.info("Done!")
    except Exception as e:
        root_logger.exception("Something went wrong!")
        sys.exit(1)