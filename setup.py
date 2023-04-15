''' First-time set up of app '''
import argparse
import logging
import sys

from dataclasses import dataclass
from typing import List

import git

logger = logging.getLogger(__file__)


def _parse_args():
    parser = argparse.ArgumentParser(description="Setup",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--verbose', '-v', help="Verbose", action='store_true', default=False)
    return parser.parse_args()


@dataclass
class GitSubmodule:
    repo: str
    dir: str
    sha: str = None


needed_modules: List[GitSubmodule] = [
    GitSubmodule("https://github.com/ChrisTopherTa54321/Wav2Lip",
                 "external/repos/wav2lip", "9db5370379fc10c7a0527bbd10629f70c068f806"),
    GitSubmodule("https://github.com/ChrisTopherTa54321/Thin-Plate-Spline-Motion-Model.git",
                 "external/repos/tpsmm", "4fb50271d7e80d09129ce4dd908b1970eb10c316")
]


if __name__ == "__main__":
    logger.info("Starting program")
    args = _parse_args()

    if args.verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)

    for module in needed_modules:
        try:
            repo = git.Repo.clone_from(module.repo, to_path=module.dir)
        except git.GitCommandError as e:
            if 'exists' in e.stderr:
                repo = git.Repo(module.dir)
            logger.error(e)

        if module.sha is not None:
            repo.head.reference = repo.commit(rev=module.sha)
        logger.info(repo)
