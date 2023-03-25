''' Interface for a Tts backend '''
from __future__ import annotations
import abc
from abc import abstractmethod
from typing import Optional, Tuple, List, Optional
from serializeable import Serializable
import numpy as np
from dataclasses import dataclass


class Tts(abc.ABC):
    '''
    An instance of a TTS backend
    '''

    class Voice(Serializable):
        '''
        An instance of a Voice supported by TTS
        '''

        @dataclass
        class JsonKeys:
            ''' Key names for the serializing '''
            NAME: str = "name"
            BACKEND: str = "backend"
            STYLE: str = "style"
            PITCH: str = "pitch"
            RATE: str = "rate"

        @abstractmethod
        def get_name(self) -> str:
            '''
            Returns:
                str: the name of the voice
            '''

        @abstractmethod
        def get_styles_available(self) -> List[str]:
            '''
            Get a list of styles available for this voice

            Returns:
                List[str]: list of styles
            '''

        @abstractmethod
        def get_style(self) -> str:
            '''
            Get the current style configured on this voice

            Returns:
                str: current style
            '''

        @abstractmethod
        def set_style(self, style: str) -> None:
            '''
            Sets the voice's style

            Args:
                style (str): style to use
            '''

        @abstractmethod
        def set_pitch(self, pitch: str) -> None:
            '''
            Sets the voice's pitch modifier
            (currently pretty azure-specific)

            Args:
                pitch (str): pitch string to use
            '''

        @abstractmethod
        def get_pitch(self) -> str:
            '''
            Gets the voice's pitch modifier

            Returns:
                pitch: voice's current pitch modifier
            '''

        @abstractmethod
        def set_rate(self, rate: str) -> None:
            '''
            Sets the voice's rate modifier
            (currently pretty azure-specific)

            Args:
                rate (str): rate string to use
            '''

        @abstractmethod
        def get_rate(self) -> str:
            '''
            Gets the voice's rate modifier

            Returns:
                Rate: voice's current rate modifier
            '''

        @abstractmethod
        def get_sampling_rate(self) -> int:
            '''
            Returns the sampling rate of the audio output by this voice

            Returns:
                int: audio sampling rate
            '''
        @abstractmethod
        def get_backend_name(self) -> str:
            '''
            Returns the name of the Voice's backend

            Returns:
                str: backend name
            '''

    @abstractmethod
    def get_voice_list(self) -> List[Tts.Voice]:
        '''
        Get a list of voices supported by this TTS engine

        Returns:
            List[Tts.Voice]: list of voices
        '''

    @abstractmethod
    def get_voice(self, name: str) -> Optional[Tts.Voice]:
        '''
        Returns a voice by name

        Returns:
            Tts.Voice: voice if valid, otherwise None
        '''

    @abstractmethod
    def synthesize(self, text: str, voice: Tts.Voice) -> Tuple[np.array, int]:
        '''
        Generate audio for the given text and voice

        Args:
            text (str): text to synthesize
            voice (Tts.Voice): voice configuration to use

        Returns:
            Tuple of (audio buffer data, sampling rate)
        '''
