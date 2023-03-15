''' Manages and performs operations on Avatars '''
from avatar.profile import Profile
from typing import List
import glob
import os
import logging

logger = logging.getLogger(__file__)


class Manager:
    def __init__(self, avatar_dir: str):
        self._root_dir = avatar_dir
        self._avatars: List[Profile] = []
        self._driving_videos: List[str] = []
        self._active_profile: Profile = None

        self.refresh()
        if len(self._avatars) > 0:
            self.active_profile = self._avatars[0]

    @property
    def active_profile(self):
        return self._active_profile

    @active_profile.setter
    def active_profile(self, profile: Profile):
        self._active_profile = profile

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
                new_profile = Profile.from_json(profile_path)
                profile_list.append(new_profile)
            except Exception as e:
                logger.warn(f"Failed to create profile from [{profile_path}]")
        return profile_list

    def _get_driving_videos(self, driving_videos_dir: str) -> List[str]:
        ''' Returns a list of videos in the driving_videos directory '''
        valid_exts = [".mp4", ".mkv", ".avi"]
        return [path for path in os.listdir(driving_videos_dir) if os.path.splitext(path.lower())[1] in valid_exts]