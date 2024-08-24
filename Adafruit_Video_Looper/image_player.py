# Author: Tobias Perschon - Updated by Tavarc Design 
# License: GNU GPLv2, see LICENSE.txt
import import os
import pygame
from time import monotonic
from collections import OrderedDict

class ImagePlayer:
    def __init__(self, config, screen, bgimage):
        """
        Initialize the ImagePlayer with configuration, screen, and background image.
        """
        self._load_config(config)
        self._screen = screen
        self._bgimage = bgimage
        self._loop = 0
        self._start_time = 0
        self._image_cache = OrderedDict()  # Initialize the image cache with OrderedDict for LRU caching
        self._cache_size_limit = config.getint('image_player', 'cache_size_limit') * 1024 * 1024  # Cache size limit in bytes
        self._current_cache_size = 0

    def _load_config(self, config):
        """
        Load configuration settings.
        """
        self._extensions = config.get('image_player', 'extensions').replace('.', '').split(',')
        self._duration = config.getint('image_player', 'duration')
        self._size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        self._bgcolor = [int(c) for c in config.get('video_looper', 'bgcolor').split(',')]
        self._scale = config.getboolean('image_player', 'scale') 
        self._center = config.getboolean('image_player', 'center') 
        self._wait_time = config.getint('video_looper', 'wait_time')

    def _get_image_size(self, pyimage):
        """
        Estimate the memory size of the pygame
        def _get_image_size(self, pyimage):
        """
        Estimate the memory size of a pygame surface (image) in bytes.
        """
        width, height = pyimage.get_size()
        depth = pyimage.get_bytesize()  # Get bytes per pixel
        return width * height * depth

    def _evict_cache(self):
        """
        Evict the least recently used image from the cache to free up memory.
        """
        if self._image_cache:
            _, evicted_image = self._image_cache.popitem(last=False)
            self._current_cache_size -= self._get_image_size(evicted_image)

    def _add_to_cache(self, image_path, pyimage):
        """
        Add an image to the cache. Evict old images if the cache size limit is exceeded.
        """
        image_size = self._get_image_size(pyimage)
        
        # Evict cache entries until there is enough space
        while self._current_cache_size + image_size > self._cache_size_limit:
            self._evict_cache()

        # Add new image to cache
        self._image_cache[image_path] = pyimage
        self._current_cache_size += image_size

    def _load_image(self, image_path):
        """
        Load an image from the cache or from disk if not already cached.
        """
        if image_path in self._image_cache:
            # Move accessed image to the end of the cache (LRU)
            pyimage = self._image_cache.pop(image_path)
            self._image_cache[image_path] = pyimage
        else:
            # Load image from disk and add to cache
            pyimage = pygame.image.load(image_path)
            self._add_to_cache(image_path, pyimage)

        return pyimage

    def play(self, image, loop=None, **kwargs):
        """
        Display the provided image file.
        """
        if loop is None:
            self._loop = image.repeats
        else:
            self._loop = loop
        if self._loop == 0:
            self._loop = 1
        
        image_path = image.filename

        if image_path != "" and os.path.isfile(image_path):
            self._blank_screen(False)
            pyimage = self._load_image(image_path)  # Use cache or load image
            image_x = 0
            image_y = 0
            screen_w, screen_h = self._size
            image_w, image_h = pyimage.get_size()
            new_image_w, new_image_h = pyimage.get_size()
            screen_aspect_ratio = screen_w / screen_h
            photo_aspect_ratio = image_w / image_h

            if self._scale:
                if screen_aspect_ratio < photo_aspect_ratio:  # Width is binding
                    new_image_w = screen_w
                    new_image_h = int(new_image_w / photo_aspect_ratio)
                    pyimage = pygame.transform.scale(pyimage, (new_image_w, new_image_h))
                elif screen_aspect_ratio > photo_aspect_ratio:  # Height is binding
                    new_image_h = screen_h
                    new_image_w = int(new_image_h * photo_aspect_ratio)
                    pyimage = pygame.transform.scale(pyimage, (new_image_w, new_image_h))
                else:  # Images have the same aspect ratio
                    pyimage = pygame.transform.scale(pyimage, (screen_w, screen_h))

            if self._center:
                if screen_aspect_ratio < photo_aspect_ratio:
                    image_y = (screen_h - new_image_h) // 2
                elif screen_aspect_ratio > photo_aspect_ratio:
                    image_x = (screen_w - new_image_w) // 2

            self._screen.blit(pyimage, (image_x, image_y))
            pygame.display.flip()

        self._start_time = monotonic()

    def is_playing(self):
        """
        Check if the image is still being displayed based on the duration and loop count.
        """
        if self._loop <= -1:  # loop one image = play forever
            return True
        
        playing = (monotonic() - self._start_time) < self._duration * self._loop
        
        if not playing and self._wait_time > 0:  # only refresh background if we wait between images
            self._blank_screen()
        
        return playing

    def stop(self, block_timeout_sec=0):
        """
        Stop the image display.
        """
        self._blank_screen()
        self._start_time = self._start_time - self._duration * self._loop

    def _blank_screen(self, flip=True):
        """
        Render a blank screen filled with the background color and optionally the background image.
        """
        self._screen.fill(self._bgcolor)
        if self._bgimage[0] is not None:
            self._screen.blit(self._bgimage[0], (self._bgimage[1], self._bgimage[2]))
        if flip:
            pygame.display.flip()

    @staticmethod
    def can_loop_count():
        return True


def create_player(config, **kwargs):
    """
    Create new image player.
    """
    return ImagePlayer(config, screen=kwargs['screen'], bgimage=kwargs['bgimage'])
