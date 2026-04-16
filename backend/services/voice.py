class VoiceService:
    async def text_to_speech(self, text: str) -> dict:
        """
        Stub for Text-to-Speech conversion.
        In a real app, this might use Google Cloud TTS, Amazon Polly, or ElevenLabs.
        """
        return {
            "status": "success",
            "message": "Speech synthesized (stub)",
            "text": text,
            "waveform_url": "/api/static/audio/sample_response.mp3"
        }

    async def speech_to_text(self, audio_data: bytes) -> str:
        """
        Stub for Speech-to-Text conversion.
        In a real app, this might use OpenAI Whisper, Google Speech-to-Text, etc.
        """
        return "This is a transcribed sample text from voice (stub)."

# Global singleton
voice_service = VoiceService()
