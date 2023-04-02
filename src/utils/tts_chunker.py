''' Class for handling chunking TTS requests '''
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import partial
from multiprocessing.dummy import Event, Queue, Lock
from multiprocessing.pool import AsyncResult, ThreadPool
from queue import Empty
from typing import Dict, List, Tuple
import traceback

import numpy as np

from tts import Tts
from utils.text_utils import TextUtils

logger = logging.getLogger(__file__)


class TtsChunker:
    @dataclass
    class ResultItem:
        chunk_id: int
        audio_data: np.array
        sample_rate: int
        text: str

    @dataclass
    class WorkerParams:
        cancel_event: Event
        workq: Queue
        lock: Lock
        voice: Tts.Voice

    @dataclass
    class WorkQueueItem:
        text: str

    @dataclass
    class AudioData:
        text: str
        data: np.array
        sample_rate: int

    def __init__(self, chunk_word_cnt: int = 256, grow_chunks: bool = True, jobs: int = 4):
        '''
        Initialize a TtsChunker

        Args:
            tts (Tts): tts interface to manage
            chunk_word_cnt (int, optional): target chunk size (number of words to send to TTS at once)
            grow_chunks (bool, optional): if True, start with a very small chunk size and grow it up to chunk_word_cnt. This gets early audio out quicker
            jobs (int, optional): number of chunks to generate at a time
        '''
        self._min_chunk_words: int = chunk_word_cnt
        self._cur_chunk_words: int = chunk_word_cnt

        if grow_chunks:
            self._cur_chunk_words = 1

        self._audio: Dict[int, TtsChunker.AudioData] = {}
        self._sampling_rate: int = 0
        self._pool: ThreadPool = ThreadPool(processes=jobs)
        self._jobs_cnt: int = jobs
        self._workq_lock: Lock = Lock()
        self._workq: Queue = Queue()
        self._pool_result: AsyncResult = None
        self._pool_cancel_event: Event = Event()
        self._read_chunk_id: int = 0
        self._worker_chunk_id: int = 0
        self._new_audio_avail_event: Event = Event()
        self._audio_complete_event: Event = Event()

    def cancel(self):
        '''
        Cancel an on-going synthesis
        '''
        if self._pool_result:
            logger.warn("Cancelling ongoing synthesis (maybe? This probably doesn't work)")
            self._pool_cancel_event.set()
            self._pool_result.wait()
            self._pool_result = None

    def reset(self):
        ''' Resets the Queue to prepare for new audio '''
        self._read_chunk_id = 0
        self._audio.clear()

    def is_done(self) -> bool:
        ''' returns true if the Queue has no work '''
        return self._pool_result is None

    def get_new_audio(self) -> Tuple[np.array, int]:
        '''
        Returns any newly available audio since the last time this function
        was called

        Returns:
            Tuple[np.array, int]: tuple of (audio data buffer, sampling rate)
        '''
        logger.info("Returning NEW audio")
        # self._assemble_audio()
        new_buffer: np.array = np.array([], dtype=np.int16)
        while self._read_chunk_id in self._audio:
            audio_data = self._audio[self._read_chunk_id]
            new_buffer = np.append(new_buffer, audio_data.data)
            self._read_chunk_id += 1
        return (new_buffer, self._sampling_rate)

    def get_all_audio(self) -> Tuple[np.array, int]:
        '''
        Returns the entire synthesized audio buffed

        Returns:
            Tuple[np.array, int]: tuple of (audio data buffer, sampling rate)
        '''
        logger.info("Returning ALL audio")
        # self._assemble_audio()
        new_buffer: np.array = np.array([], dtype=np.int16)
        for chunk_id in sorted(self._audio.keys()):
            audio_data = self._audio[chunk_id]
            new_buffer = np.append(new_buffer, audio_data.data)
        return (new_buffer, self._sampling_rate)

    def start_synthesis(self, text: str, voice: Tts.Voice):
        '''
        Begin synthesizing a large block of text.

        Cancels any on-going synthesis.

        Args:
            text (str): text to speak
            voice (Tts.Voice): voice parameters to use
        '''
        if self._pool_result:
            self.cancel()

        self.reset()

        # Assemble the sentences into a list and prepare the work queue
        sentences: List[str] = TextUtils.split_sentences(text)
        for sentence in sentences:
            self._workq.put(TtsChunker.WorkQueueItem(text=sentence))
        self._worker_chunk_id = 0
        worker_ids: List[int] = list(range(1, self._jobs_cnt+1))

        self._sampling_rate = voice.get_sampling_rate()
        params: TtsChunker.WorkerParams = TtsChunker.WorkerParams(
            cancel_event=self._pool_cancel_event, workq=self._workq, lock=self._workq_lock, voice=voice)
        self._pool_result = self._pool.map_async(func=partial(
            self._worker_func, params), iterable=worker_ids, callback=self._result_ready)

    def wait_for_audio(self, timeout: float = None) -> bool:
        ''' Checks for any audio, optionally blocking until audio is available'''
        return len(self._audio) > 0 or self._new_audio_avail_event.wait(timeout)

    def wait_for_new_audio(self, timeout: float = None) -> bool:
        ''' Checks for unprocessed audio, optionally blocking until audio is available'''
        end_time = time.time() + timeout if timeout else None
        audio_ready = self._read_chunk_id in self._audio

        while not (audio_ready or self.audio_done):
            remaining_timeout = end_time - time.time() if end_time else None
            signaled = self._new_audio_avail_event.wait(timeout=remaining_timeout)
            if signaled:
                self._new_audio_avail_event.clear()
                audio_ready = self._read_chunk_id in self._audio
            else:
                break

        return audio_ready

    def wait_for_audio_complete(self, timeout: float = None) -> bool:
        return self._audio_complete_event.wait(timeout)

    def _get_chunk_id(self):
        ''' Returns the next chunk id '''
        chunk_id = self._worker_chunk_id
        self._worker_chunk_id += 1
        return chunk_id

    def _worker_func(self, params: TtsChunker.WorkerParams, worker_id: int):
        '''
        Background worker function to generate chunks of TTS audio
        '''
        logger.info(f"Worker {worker_id} starting up")
        done: bool = False

        while not done and not params.cancel_event.is_set():

            # Grab the lock so we can grab multiple consecutive chunks
            with params.lock:
                chunk_id: int = self._get_chunk_id()
                text_to_speak: str = ""
                word_cnt: int = 0
                while (word_cnt < self._cur_chunk_words) and not done:
                    try:
                        work_item: TtsChunker.WorkQueueItem = params.workq.get(timeout=0.0)
                        text_to_speak += f" {work_item.text}"
                        word_cnt += len(TextUtils.split_words(work_item.text))
                    except Empty as e:
                        done = True
                    except Exception as e:
                        traceback.print_exception(e)
                        logger.error(f"WorkQueue Error: {e}")

                if self._cur_chunk_words < self._min_chunk_words:
                    self._cur_chunk_words = min(5*self._cur_chunk_words, self._min_chunk_words)

            if text_to_speak:
                logger.info(f"Worker {worker_id} got work item: {text_to_speak}")
                start = time.time()
                try:
                    sample_rate, audio_data = params.voice.synthesize(text=text_to_speak)
                except Exception as e:
                    traceback.print_exception(e)
                    logger.error(f"Synthesize Error: {e}")
                    audio_data, sample_rate = None, 0

                self._audio[chunk_id] = TtsChunker.AudioData(
                    text=text_to_speak, data=audio_data, sample_rate=sample_rate)
                self._new_audio_avail_event.set()
                elapsed = time.time() - start
                logger.info(
                    f"Done working on {chunk_id}. Took {elapsed:.2f} to process {len(text_to_speak)} characters ({len(text_to_speak)/elapsed:.2f}cps)")
        logger.info(f"Worker {worker_id} exiting")

    def _result_ready(self, *args, **kwargs):
        '''
        Callback when all results are ready
        '''
        # self._assemble_audio()
        logger.info("Synthesis complete")
        self._pool_result = None
        self._audio_complete_event.set()

    @property
    def audio_done(self) -> bool:
        return self._audio_complete_event.is_set()
