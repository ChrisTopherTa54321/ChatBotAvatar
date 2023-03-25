''' Handles creating Voices '''
from typing import Dict, Any, Optional
from tts import Tts

# TODO: Deal with same name in different backends


class VoiceFactory:
    _tts_map: Dict[str, Tts] = {}
    _voice_map: Dict[str, Tts.Voice] = {}

    @classmethod
    def get_voices(cls) -> Dict[str, Tts.Voice]:
        if not cls._voice_map:
            cls._build_voice_map()
        return cls._voice_map

    @classmethod
    def get_voice(cls, voice_name: str) -> Optional[Tts.Voice]:
        return cls._voice_map.get(voice_name, None)

    @classmethod
    def register_tts(cls, name: str, tts: Tts):
        cls._tts_map[name] = tts
        cls._voice_map.clear()

    @classmethod
    def get_backend(cls, voice: Tts.Voice) -> Tts:
        ''' Gets the backend for a given voice '''
        return cls._tts_map.get(voice.get_backend_name(), None)

    @classmethod
    def create_voice_from_dict(cls, voice_info: Dict[str, Any]) -> Tts.Voice:
        tts_name: str = voice_info[Tts.Voice.JsonKeys.NAME]
        voice = VoiceFactory.get_voice(tts_name)
        return voice

    @classmethod
    def _build_voice_map(cls) -> None:
        cls._voice_map.clear()
        for backend_name, tts in cls._tts_map.items():
            for voice in tts.get_voice_list():
                cls._voice_map[voice.get_name()] = voice
