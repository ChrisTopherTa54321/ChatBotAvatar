''' Class representing a single avatar '''
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from io import TextIOWrapper
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np
from PIL import Image
from typing_extensions import override

from serializeable import Serializable
from tts import Tts
from utils.voice_factory import VoiceFactory
from utils.image_utils import ImageUtils


class Profile(Serializable):
    DEFAULT_NAME: str = "Anonymous Avatar"

    @dataclass
    class Filenames:
        JSON: str = "profile.json"
        PREVIEW: str = "profile.png"

    @dataclass
    class JsonKeys:
        ''' Key names for the profile.json '''
        FRIENDLY_NAME: str = "friendly_name"
        PREVIEW_IMAGE: str = "preview_image"
        VOICE_INFO: str = "voice_info"

    def __init__(self, profile_root_dir: Path, friendly_name: str = DEFAULT_NAME):
        self._root_dir: Path = Path(profile_root_dir)
        self._name: str = os.path.basename(self._root_dir)
        self._friendly_name: str = friendly_name
        self._preview_image: Optional[np.ndarray] = None
        self._voice: Tts.Voice = None

    def save(self, output_dir: Path, overwrite: bool = True):
        '''
        Saves the profile to the output directory

        Args:
            output_dir (Path): profile directory to write to
            overwrite (bool, optional): if True then overwrite existing directories
        '''
        output_dir = Path(output_dir)
        os.makedirs(output_dir, exist_ok=overwrite)
        data = self.as_dict()
        ImageUtils.copy_or_save(self.preview_image, os.path.join(output_dir, Profile.Filenames.PREVIEW))
        with open(os.path.join(output_dir, Profile.Filenames.JSON), "w") as fhndl:
            json.dump(data, fhndl)

    @classmethod
    def from_profile_directory(cls, profile_directory: Path) -> Profile:
        '''
        Create a Profile from a profile directory

        Args:
            profile_directory (Path): path to profile directory

        Returns:
            Profile: profile initialized from the given directory
        '''
        profile_json_path = os.path.join(profile_directory, Profile.Filenames.JSON)
        with open(profile_json_path, 'r') as fhndl:
            data = json.load(fhndl)

        new_profile: Profile = Profile(profile_root_dir=profile_directory).from_dict(data)
        return new_profile

    @property
    def name(self) -> str:
        ''' The name of the avatar  '''
        return self._name

    @property
    def friendly_name(self) -> str:
        ''' The friendly name of the avatar '''
        return self._friendly_name

    @friendly_name.setter
    def friendly_name(self, new_name: str):
        ''' Set the friendly name of the avatar '''
        self._friendly_name = new_name

    @property
    def preview_image(self) -> Image.Image:
        ''' returns an image for this avatar '''
        return ImageUtils.open_or_blank(self._preview_image)

    @preview_image.setter
    def preview_image(self, image: Union[np.ndarray, Path]):
        self._preview_image = ImageUtils.image_data(image) if image is not None else None

    @property
    def voice(self) -> Tts.Voice:
        return self._voice

    @voice.setter
    def voice(self, new_voice: Tts.Voice):
        self._voice = new_voice

    @override
    def from_dict(self, info: Dict[str, Any]) -> Profile:
        ''' Loads data from a dict into the Profile '''
        self._friendly_name = info.get(Profile.JsonKeys.FRIENDLY_NAME, Profile.DEFAULT_NAME)
        voice_info = info.get(Profile.JsonKeys.VOICE_INFO, None)
        if voice_info:
            self._voice = VoiceFactory.create_voice_from_dict(voice_info)
        else:
            self._voice = None
        preview_image_path = info.get(Profile.JsonKeys.PREVIEW_IMAGE, None)
        if preview_image_path:
            self._preview_image = ImageUtils.open_or_blank(self._root_dir.joinpath(preview_image_path))
        return self

    @override
    def as_dict(self) -> Dict[str, Any]:
        ret: Dict[str, Any] = {}
        ret[Profile.JsonKeys.FRIENDLY_NAME] = self._friendly_name
        ret[Profile.JsonKeys.PREVIEW_IMAGE] = Profile.Filenames.PREVIEW
        if self._voice:
            voice_json = self._voice.as_dict()
            ret[Profile.JsonKeys.VOICE_INFO] = voice_json
        return ret
