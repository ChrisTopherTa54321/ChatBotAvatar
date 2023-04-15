''' First-time set up of app '''
import argparse
import logging
import sys
import os
import subprocess
import shutil

from dataclasses import dataclass
from typing import List


logger = logging.getLogger(__file__)


def _parse_args():
    parser = argparse.ArgumentParser(description="Setup",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--verbose', '-v', help="Verbose", action='store_true', default=False)
    return parser.parse_args()


@dataclass
class GitSubmodule:
    repo: str
    dir_name: str
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

    subprocess.run([sys.executable, "-m", "pip", "install", "-U", "-r", "requirements.txt"])

    import git
    for module in needed_modules:
        try:
            if os.path.isdir(module.dir_name):
                repo = git.Repo(module.dir_name)
            else:
                repo = git.Repo.clone_from(module.repo, to_path=module.dir_name)
        except git.GitCommandError as e:
            logger.error(e)

        if module.sha is not None:
            repo.head.reference = repo.commit(rev=module.sha)

    sample_driving_video = os.path.join("external/repos/tpsmm", "tpsmm", "assets", "driving.mp4")
    try:
        shutil.copyfile(sample_driving_video, os.path.join("avatar/driving_videos/sample.mp4"))
    except Exception as e:
        pass


    try:
        output = subprocess.run("ffmpeg", stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
    except Exception as e:
        logger.error("\n\n\n***********************\nCould not find ffmpeg!\nffmpeg must be installed and accessible in your system path\n***********************\n")

    logger.info("Setup complete. Run application with 'webui'")