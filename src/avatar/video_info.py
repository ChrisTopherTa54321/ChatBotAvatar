''' Class representing a video file '''
from __future__ import annotations
from pathlib import Path
from PIL import Image
from utils.image_utils import ImageUtils
from typing import Optional, List
import cv2
import os


class VideoInfo():
    IMG_EXTS = ['.png', '.jpg']
    VID_EXTS = ['.webm', '.mp4', '.mkv', '.gif', '.avi']

    def __init__(self, video_path: Path):
        self._path: Path = video_path
        self._thumbnail: Image.Image = None

    @property
    def thumbnail(self) -> Image.Image:
        if not self._thumbnail:
            self._thumbnail = self._load_thumbnail()
        return self._thumbnail

    @property
    def path(self) -> Path:
        return self._path

    def _load_thumbnail(self) -> Optional[Image.Image]:
        thumbnail_path = self._locate_thumbnail()
        if not thumbnail_path:
            self.refresh_thumbnail()
            thumbnail_path = self._locate_thumbnail()
        if thumbnail_path:
            return Image.open(thumbnail_path)
        return None

    def _locate_thumbnail(self) -> Optional[Path]:
        base, _ = os.path.splitext(self._path)
        for ext in VideoInfo.IMG_EXTS:
            filename = base + ext
            if os.path.exists(filename):
                return Path(filename)
        return None

    def refresh_thumbnail(self, frame_idx=None):
        ''' Re-creates the thumbnail image from the video file '''
        vid: cv2.VideoCapture = cv2.VideoCapture(self.path)
        if vid:
            if frame_idx:
                vid.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            success, img = vid.read()
            if success:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                # Existing preview to overwrite?
                preview_name = self._locate_thumbnail()
                if not preview_name:
                    base, _ = os.path.splitext(self._path)
                    preview_name = base + VideoInfo.IMG_EXTS[0]
                img.save(preview_name)

    @classmethod
    def list_directory(self, path: Path, valid_exts: List[str] = None) -> List[VideoInfo]:
        ''' Returns a list of videos in the driving_videos directory '''
        if not os.path.isdir(path):
            return []
        valid_exts = valid_exts or VideoInfo.VID_EXTS
        return [VideoInfo(video_path=os.path.join(path, file)) for file in os.listdir(path) if os.path.splitext(file.lower())[1] in valid_exts]
