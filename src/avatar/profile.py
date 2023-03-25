''' Class representing a single avatar '''
from __future__ import annotations
from typing import Dict, Any, Optional, Union
from typing_extensions import override
from dataclasses import dataclass
from tts import Tts
from utils.voice_factory import VoiceFactory
from serializeable import Serializable
import numpy as np
from PIL import Image
import os
import json
from io import TextIOWrapper


class Profile(Serializable):
    @dataclass
    class Filenames:
        JSON: str = "profile.json"
        PREVIEW: str = "profile.png"

    @dataclass
    class JsonKeys:
        ''' Key names for the profile.json '''
        NAME: str = "name"
        PROFILE_DIR: str = "directory"
        PREVIEW_IMAGE: str = "preview_image"
        VOICE_INFO: str = "voice_info"

    def __init__(self, profile_dir: str, name: str = "Nameless"):
        self._name: str = name
        self._dir: str = profile_dir
        self._preview_image_path: Optional[str] = None
        self._voice: Tts.Voice = None

    def save(self, profile_image: Optional[Union[np.ndarray, Image.Image]] = None):
        ''' Saves the profile to the profile_dir '''
        if profile_image is not None:
            if isinstance(profile_image, np.ndarray):
                profile_image = Image.fromarray(profile_image)
            profile_image.save(self.preview_image_path)
        data = self.as_dict()

        os.makedirs(os.path.dirname(self.profile_json_path), exist_ok=True)
        with open(self.profile_json_path, "w") as fhndl:
            json.dump(data, fhndl)

    @classmethod
    def from_stream(cls, stream: TextIOWrapper) -> Profile:
        data = json.load(stream)
        new_profile: Profile = Profile(profile_dir=data[Profile.JsonKeys.PROFILE_DIR], name=data[Profile.JsonKeys.NAME])
        voice_info = data.get(Profile.JsonKeys.VOICE_INFO, None)
        if voice_info:
            new_profile.voice = VoiceFactory.create_voice_from_dict(voice_info)
        return new_profile

    @classmethod
    def from_json_file(cls, json_path: str) -> Profile:
        return cls.from_stream(open(json_path, "r"))

    @property
    def name(self):
        ''' The name of the Avatar  '''
        return self._name

    @property
    def preview_image(self) -> np.ndarray:
        ''' returns an image for this avatar '''

    @property
    def preview_image_path(self):
        ''' The path to the preview image for this avatar'''
        return os.path.join(self._dir, Profile.Filenames.PREVIEW)

    @property
    def profile_json_path(self) -> str:
        ''' The path to the JSON for this avatar'''
        return os.path.join(self._dir, Profile.Filenames.JSON)

    @property
    def directory(self) -> str:
        return self._dir

    @property
    def voice(self) -> Tts.Voice:
        return self._voice

    @voice.setter
    def voice(self, new_voice: Tts.Voice):
        self._voice = new_voice

    @override
    def from_dict(self, info: Dict[str, Any]) -> Any:
        ''' Loads data from a dict into the Profile '''
        self._name = data.get(Profile.JsonKeys.NAME, self._name)
        self._preview_image_path = data.get(Profile.JsonKeys.PREVIEW_IMAGE, self._preview_image_path)
        voice_info = data.get(Profile.JsonKeys.VOICE_INFO, None)
        if voice_info:
            self._voice = VoiceFactory.from_dict(voice_info)
        else:
            self._voice = None

    @override
    def as_dict(self) -> Dict[str, Any]:
        ret: Dict[str, Any] = {}
        ret[Profile.JsonKeys.NAME] = self._name
        ret[Profile.JsonKeys.PROFILE_DIR] = self._dir
        ret[Profile.JsonKeys.PREVIEW_IMAGE] = self._preview_image_path
        if self._voice:
            voice_json = self._voice.as_dict()
            ret[Profile.JsonKeys.VOICE_INFO] = voice_json
        return ret

    # @ classmethod
    # def from_json(cls, profile_json_path: str) -> Profile:
    #     '''
    #     Return an Avatar from a JSON file

    #     Args:
    #         path (str): path to JSON

    #     Returns:
    #         Profile: An initialized Profile
    #     '''
    #     profile_data: Dict[str, Any] = json.load(open(profile_json_path))
    #     new_profile = Profile(profile_dir=os.path.dirname(profile_json_path))
    #     new_profile._load_dict(profile_data)

    #     return new_profile

    # def to_json(self) -> str:
    #     '''
    #     Returns the JSON avatar profile

    #     Returns:
    #         str: json avatar profile
    #     '''
    #     return json.dumps(self._as_dict())
