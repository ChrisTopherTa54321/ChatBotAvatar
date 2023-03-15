''' Class representing a single avatar '''
from __future__ import annotations
from typing import Dict, Any, Optional
from dataclasses import dataclass
import os
import json


class Profile:
    @dataclass
    class JsonKeys:
        ''' Key names for the profile.json '''
        NAME: str = "name"
        PREVIEW_IMAGE: str = "preview_image"

    def __init__(self, profile_dir: str, name: str = "Nameless"):
        self._name: str = name
        self._dir: str = profile_dir
        self._preview_image_path: Optional[str] = None

    @property
    def name(self):
        ''' The name of the Avatar  '''
        return self._name

    @property
    def preview_image(self):
        ''' The path to the preview image for this Avatar'''
        return os.path.join(self._dir, self._preview_image_path)

    def _load_dict(self, data: Dict[str, Any]) -> None:
        ''' Loads data from a dict into the Profile '''
        self._name = data.get(Profile.JsonKeys.NAME, self._name)
        self._preview_image_path = data.get(Profile.JsonKeys.PREVIEW_IMAGE, self._preview_image_path)

    def _as_dict(self) -> Dict[str, Any]:
        ''' Export this profile data as a dictionary '''
        data: Dict[str, Any] = {}
        data[Profile.JsonKeys.NAME] = self._name
        data[Profile.JsonKeys.PREVIEW_IMAGE] = self._preview_image_path
        return data

    @ classmethod
    def from_json(cls, profile_json_path: str) -> Profile:
        '''
        Return an Avatar from a JSON file

        Args:
            path (str): path to JSON

        Returns:
            Profile: An initialized Profile
        '''
        profile_data: Dict[str, Any] = json.load(open(profile_json_path))
        new_profile = Profile(profile_dir=os.path.dirname(profile_json_path))
        new_profile._load_dict(profile_data)

        return new_profile

    def to_json(self) -> str:
        '''
        Returns the JSON avatar profile

        Returns:
            str: json avatar profile
        '''
        return json.dumps(self._as_dict())
