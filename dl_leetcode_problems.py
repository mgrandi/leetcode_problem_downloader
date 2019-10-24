#!/usr/bin/env python3

import leetcode_dl
from leetcode_dl import downloader
from leetcode_dl import utils

# library imports
import argparse
import logging
import logging.config
import json
import sys

import arrow
import logging_tree




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

    # silence urllib3 (requests) logger because its noisy
    requests_packages_urllib_logger = logging.getLogger("requests.packages.urllib3")
    requests_packages_urllib_logger.setLevel("INFO")
    urllib_logger = logging.getLogger("urllib3")
    urllib_logger.setLevel("INFO")

    parser.add_argument("username", type=str, help="leetcode username")
    parser.add_argument("password", type=str, help="leetcode password")
    parser.add_argument("path_to_save_to", metavar="path-to-save-to",
        type=utils.isDirectoryType, help="the path to download the problems to")
    parser.add_argument("--version", action="version", help="show the program version", version=leetcode_dl.__version__)

    group = parser.add_mutually_exclusive_group()

    group.add_argument("--verbose", action="store_true", help="Increase logging verbosity")
    group.add_argument("--logging-config", dest="logging_config", type=utils.isFileType, help="Specify a JSON file representing logging configuration")

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
        app = downloader.Application(root_logger.getChild("app"), parsed_args)
        app.run()

        root_logger.info("Done!")
    except Exception as e:
        root_logger.exception("Something went wrong!")
        sys.exit(1)