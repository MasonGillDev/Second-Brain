"""Wake-word detection via openWakeWord.

Feed 80 ms (1280-sample) int16 frames to detect(); it returns True when the
configured wake word fires above threshold. Fully offline, no API key.
"""

import numpy as np

from . import config


class WakeWordDetector:
    def __init__(self):
        import openwakeword
        from openwakeword.model import Model

        # Downloads pretrained wake-word + feature models on first run (cached
        # in the openwakeword package dir thereafter).
        openwakeword.utils.download_models()

        print(f"  [wake] Loading model {config.WAKE_WORD!r}...")
        self.model = Model(
            wakeword_models=[config.WAKE_WORD],
            inference_framework=config.OWW_INFERENCE_FRAMEWORK,
        )
        self.threshold = config.WAKE_THRESHOLD
        self._key = self._resolve_key()
        print("  [wake] Ready.")

    def _resolve_key(self) -> str:
        """openWakeWord keys predictions by model name; match ours leniently."""
        keys = list(self.model.models.keys())
        if config.WAKE_WORD in keys:
            return config.WAKE_WORD
        for k in keys:
            if config.WAKE_WORD in k:
                return k
        return keys[0] if keys else config.WAKE_WORD

    def detect(self, frame_int16: np.ndarray) -> float:
        """Return the wake-word score for one 16 kHz int16 frame."""
        scores = self.model.predict(frame_int16)
        return float(scores.get(self._key, 0.0))

    def triggered(self, frame_int16: np.ndarray) -> bool:
        return self.detect(frame_int16) >= self.threshold

    def reset(self) -> None:
        """Clear the model's internal audio buffer between activations."""
        self.model.reset()
