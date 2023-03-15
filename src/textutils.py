''' Utilities for text strings '''

from typing import List, Callable, Tuple
import nltk
import os
import re
from nltk.tokenize import sent_tokenize
from functools import partial


class TextUtils:
    class Settings:
        '''
        Settings for TextUtils class
        '''
        _data_dir = "models"

        @property
        def data_dir(self):
            return self._data_dir

        @data_dir.setter
        def data_dir(self, path: str):
            self._data_dir = path
            nltk.data.path = [path] + nltk.data.path
    settings: Settings = Settings()

    _nltk_package_pattern: re.Pattern = re.compile(r".*nltk\.download\('(?P<package_name>.*)'\)", re.DOTALL)
    _TRIM_CHARS = "\r\n\t: "

    @classmethod
    def split_sentences(cls, text: str) -> List[str]:
        '''
        splits text in to sentences

        Args:
            text (str): input text

        Returns:
            List[str]: list of sentences extracted from input text
        '''
        split = cls._download_wrapper(partial(sent_tokenize, text))
        return split

    @classmethod
    def split_speakers(cls, text: str, initial_speaker: str) -> List[Tuple[str, str]]:
        '''
        splits text into speakers, looking for '\nSpeaker:' patterns

        Args:
            text (str): text to split
            initial_speaker (str): initial speaker if the text does not start with a speaker

        Returns:
            List[Tuple[str,str]]: list of (speaker, message) pairs
        '''
        ret: List[Tuple] = []
        _speaker_pattern: re.Pattern = re.compile(r".*?([^\s]+):.*", flags=re.DOTALL)
        cur_speaker = initial_speaker
        while text:
            matches = _speaker_pattern.match(text)
            if not matches:
                # No match, remaining text is assigned to current speaker
                ret.append((cur_speaker, text.strip(TextUtils._TRIM_CHARS)))
                text = ""
            else:
                startPos = matches.start(1)
                if 0 == startPos:
                    cur_speaker = matches.group(1).lower()
                    text = text[len(cur_speaker):]
                    # Text is currently at the speaker. Extract it and continue looping
                else:
                    # Text up until startPos is assigned to current speaker
                    speaker_text = text[:startPos]
                    ret.append((cur_speaker, speaker_text.strip(TextUtils._TRIM_CHARS)))
                    text = text[startPos:]
        return ret

    @classmethod
    def _download_wrapper(cls, func: Callable):
        '''Wraps a nltk function to download models if necessary

        Repeatedly calls functions, downloading models on failure,
        until the failures are not caused by missing models

        Args:
            func (Callable): function to wrap
        '''
        last_error: str = None
        while True:
            try:
                try:
                    ret = func()
                    return ret
                except Exception as e:
                    if last_error == str(e):
                        raise StopIteration(e)
                    last_error = str(e)
                    raise
            except LookupError as e:
                match = TextUtils._nltk_package_pattern.match(str(e))
                if match:
                    nltk.download(match.group("package_name"))
            except StopIteration as e:
                raise e.value

        return ret
