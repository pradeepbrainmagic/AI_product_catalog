from backend.voice.speech_to_text import speech_to_text


audio_file = "data/voice_test/english_test.wav"


result = speech_to_text.transcribe(
    audio_file
)


print("\n==============================")
print("SPEECH TO TEXT RESULT")
print("==============================")

print("Text     :", result["text"])
print("Language :", result["language"])