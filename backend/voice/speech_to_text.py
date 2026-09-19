from faster_whisper import WhisperModel


class SpeechToText:
    """
    Multilingual Speech-to-Text service.

    Uses Whisper to:
    1. Transcribe user speech
    2. Automatically detect language
    3. Return both text and language
    """

    def __init__(
        self,
        model_size="small",
        device="cpu",
        compute_type="int8"
    ):

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )

    # =========================================================
    # TRANSCRIBE AUDIO
    # =========================================================

    def transcribe(self, audio_file):
        """
        Convert speech into text.

        Returns:

        {
            "text": "...",
            "language": "ta"
        }
        """

        segments, info = self.model.transcribe(
            audio_file,
            beam_size=5
        )

        # -----------------------------------------------------
        # COMBINE ALL SEGMENTS
        # -----------------------------------------------------

        text_parts = []

        for segment in segments:

            text = segment.text.strip()

            if text:
                text_parts.append(text)

        text = " ".join(text_parts).strip()

        # -----------------------------------------------------
        # DETECTED LANGUAGE
        # -----------------------------------------------------

        language = info.language

        # -----------------------------------------------------
        # RETURN RESULT
        # -----------------------------------------------------

        return {
            "text": text,
            "language": language
        }


# =========================================================
# SINGLETON SERVICE
# =========================================================

speech_to_text = SpeechToText()