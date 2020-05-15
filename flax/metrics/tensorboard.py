# Copyright 2020 The Flax Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Write Summaries from JAX for use with Tensorboard.
"""

import sys
import warnings
import matplotlib as mpl
# Necessary to prevent attempted Tk import:
with warnings.catch_warnings():
  warnings.simplefilter('ignore')
  if 'google.colab' in sys.modules or 'ipykernel' in sys.modules:
    pass
  else:
    mpl.use('Agg')
# pylint: disable=g-import-not-at-top
import numpy as onp
import tensorflow.compat.v2 as tf
from tensorflow.compat.v2.io import gfile


class SummaryWriter(object):
  """Saves data in event and summary protos for tensorboard."""

  def __init__(self, log_dir):
    """Create a new SummaryWriter.

    Args:
      log_dir: path to record tfevents files in.
    """
    # If needed, create log_dir directory as well as missing parent directories.
    if not gfile.isdir(log_dir):
      gfile.makedirs(log_dir)

    self._event_writer = tf.summary.create_file_writer(log_dir, 10, 120, None)
    self._closed = False

  def close(self):
    """Close SummaryWriter. Final!"""
    if not self._closed:
      self._event_writer.close()
      self._closed = True
      del self._event_writer

  def flush(self):
    self._event_writer.flush()

  def scalar(self, tag, value, step):
    """Saves scalar value.

    Args:
      tag: str: label for this data
      value: int/float: number to log
      step: int: training step
    """
    value = float(onp.array(value))
    with self._event_writer.as_default():
      tf.summary.scalar(name=tag, data=value, step=step)

  def image(self, tag, image, step):
    """Saves RGB image summary from onp.ndarray [H,W], [H,W,1], or [H,W,3].

    Args:
      tag: str: label for this data
      image: ndarray: [H,W], [H,W,1], [H,W,3] save image in greyscale or colors.
        Pixel values could be either uint8 or float.
        Floating point values should be in range [0, 1).
      step: int: training step
    """
    image = onp.array(image)
    if len(onp.shape(image)) == 2:
      image = image[:, :, onp.newaxis]
    if onp.shape(image)[-1] == 1:
      image = onp.repeat(image, 3, axis=-1)
    # tf.summary.image expects image to have shape [k, h, w, c] where,
    # k = number of samples, h = height, w = width, c = number of channels.
    image = image[onp.newaxis, :, :, :]

    # Convert to tensor value as tf.summary.image expects data to be a tensor.
    image = tf.convert_to_tensor(image)
    with self._event_writer.as_default():
      tf.summary.image(name=tag, data=image, step=step)

  def audio(self, tag, audiodata, step, sample_rate=44100, max_outputs=3):
    """Saves audio as wave.

    NB: single channel only right now.

    Args:
      tag: str: label for this data
      audiodata: ndarray [Nsamples, Nframes, Nchannels]: audio data to
        be saved as wave. The data will be clipped to [-1.0, 1.0].
      step: int: training step
      sample_rate: sample rate of passed in audio buffer
      max_outputs: At most this many audio clips will be emitted at each
        step. Defaults to 3.
    """
    # tf.summary.audio expects the audio data to have floating values in
    # [-1.0, 1.0].
    audiodata = onp.clip(onp.array(audiodata), -1, 1)

    # Convert to tensor value as tf.summary.audio expects data to be a tensor.
    audio = tf.convert_to_tensor(audiodata, dtype=tf.float32)
    with self._event_writer.as_default():
      tf.summary.audio(
          name=tag, data=audio, sample_rate=sample_rate, step=step,
          max_outputs=max_outputs, encoding='wav')

  def histogram(self, tag, values, step, bins=None):
    """Saves histogram of values.

    Args:
      tag: str: label for this data
      values: ndarray: will be flattened by this routine
      step: int: training step
      bins: number of bins in histogram
    """
    values = onp.array(values)
    values = onp.reshape(values, -1)
    with self._event_writer.as_default():
      tf.summary.histogram(name=tag, data=values, step=step, buckets=bins)

  def text(self, tag, textdata, step):
    """Saves a text summary.

    Args:
      tag: str: label for this data
      textdata: string
      step: int: training step
    Note: markdown formatting is rendered by tensorboard.
    """
    if not isinstance(textdata, (str, bytes)):
      raise ValueError('textdata should be of the type `str` or `bytes`.')
    with self._event_writer.as_default():
      tf.summary.text(name=tag, data=tf.constant(textdata), step=step)
