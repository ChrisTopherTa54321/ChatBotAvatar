''' Manages and performs operations on Avatars '''
from avatar.profile import Profile
from utils.image_utils import ImageUtils
from typing import List
from sanitize_filename import sanitize
import glob
import json
import os
import logging
import shutil
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__file__)


class Manager:
    @dataclass
    class Directories:
        AVATARS = "avatars"
        DRIVING_VIDEOS = "driving_videos"

    def __init__(self, avatar_dir: Path):
        self._root_dir: Path = Path(avatar_dir)
        self._avatars: List[Profile] = []
        self._driving_videos: List[str] = []

    @property
    def avatar_dir(self) -> Path:
        return self._root_dir.joinpath(Manager.Directories.AVATARS)

    @property
    def driving_videos_dir(self) -> Path:
        return self._root_dir.joinpath(Manager.Directories.DRIVING_VIDEOS)

    @classmethod
    def sanitize_name(cls, name: str) -> str:
        ''' Returns a sanitized version of name '''
        name = sanitize(name.lower())
        name = name.replace(" ", "_")
        return name

    def create_new_profile(self, profile_name: str) -> Profile:
        profile_path = self.avatar_dir.joinpath(Manager.sanitize_name(profile_name))
        new_profile = Profile(profile_root_dir=profile_path)
        new_profile.save(output_dir=profile_path, overwrite=False)
        return new_profile

    def delete_profile(self, profile: Profile) -> None:
        profile_dir: Path = self.avatar_dir.joinpath(Path(profile.name))
        shutil.rmtree(profile_dir)

    def save_profile(self, profile: Profile, overwrite: bool = False) -> None:
        profile_path = os.path.join(self.avatar_dir, profile.name)
        profile.save(output_dir=profile_path, overwrite=overwrite)

    def refresh(self) -> None:
        ''' Updates the list of avatars '''
        self._avatars = self._get_profiles(os.path.join(self._root_dir, "avatars"))
        self._driving_videos = self._get_driving_videos(os.path.join(self._root_dir, "driving_videos"))

    def list_avatars(self) -> List[Profile]:
        ''' Returns a list of available avatars '''
        return self._avatars.copy()

    def _get_profiles(self, avatars_dir: str) -> List[Profile]:
        ''' Returns a list of profiles in an Avatar directory '''
        search_glob: str = os.path.join(avatars_dir, "*", "profile.json")
        profile_list: List[Profile] = []
        for profile_path in glob.glob(search_glob):
            try:
                new_profile = Profile.from_profile_directory(os.path.dirname(profile_path))
                profile_list.append(new_profile)
            except Exception as e:
                logger.warn(f"Failed to create profile from [{profile_path}] : {e}")
        return profile_list

    def _get_driving_videos(self, driving_videos_dir: str) -> List[str]:
        ''' Returns a list of videos in the driving_videos directory '''
        valid_exts = [".mp4", ".mkv", ".avi"]
        return [path for path in os.listdir(driving_videos_dir) if os.path.splitext(path.lower())[1] in valid_exts]
