import numpy as np

from vpn_counter.audio import AudioBuffer


def test_audio_windows_keep_correct_absolute_positions():
    buffer = AudioBuffer(sample_rate=10, seconds=3)
    buffer.append(np.arange(20, dtype=np.float32))
    buffer.append(np.arange(20, 40, dtype=np.float32))
    assert buffer.bounds == (10, 40, 0)
    window = buffer.window(35, seconds=2)
    assert (window.start_sample, window.end_sample) == (15, 35)
    np.testing.assert_array_equal(window.samples, np.arange(15, 35))


def test_reset_discards_audio_without_reusing_the_timeline():
    buffer = AudioBuffer(sample_rate=10)
    buffer.append(np.ones(20))
    buffer.clear()
    assert buffer.bounds == (20, 20, 1)
    assert buffer.window(20, 2) is None
    buffer.append(np.ones(10))
    assert buffer.window(30, 2).start_sample == 20


def test_microphone_overflow_breaks_overlap_history():
    buffer = AudioBuffer(sample_rate=10)
    buffer.append(np.ones(20))
    buffer.append(np.ones(5), overflow=True)
    assert buffer.bounds == (20, 25, 1)
    assert buffer.overflows == 1
