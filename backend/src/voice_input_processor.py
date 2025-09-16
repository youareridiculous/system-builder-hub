"""
Priority 26: Voice Input Processor

This module handles voice memo uploads and microphone input,
transcribing audio to text and converting to structured system instructions.
"""

import os
import json
import uuid
import time
import logging
import tempfile
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from enum import Enum
try:
    import pyaudio
    import wave
    import audioop
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    # Mock classes for when pyaudio is not available
    class pyaudio:
        class PyAudio:
            def __init__(self):
                pass
            def open(self, *args, **kwargs):
                return MockAudioStream()
            def close(self):
                pass
    
    class MockAudioStream:
        def __init__(self):
            pass
        def read(self, *args, **kwargs):
            return b'\x00' * 1024
        def write(self, *args, **kwargs):
            pass
        def stop_stream(self):
            pass
        def close(self):
            pass

import numpy as np
from context_engine import VoiceTranscript, PromptType, ContextEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProcessingStatus(str, Enum):
    """Status of voice processing operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AudioMetadata:
    """Metadata for audio files"""
    duration_seconds: float
    sample_rate: int
    channels: int
    bit_depth: int
    file_size_bytes: int
    format: str
    encoding: str

@dataclass
class TranscriptionResult:
    """Result of audio transcription"""
    transcript_id: str
    audio_file_path: str
    transcript_text: str
    confidence_score: float
    duration_seconds: float
    language: str
    metadata: Dict[str, Any]
    timestamp: datetime

class AudioRecorder:
    """Records audio from microphone"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.frames = []
        self.is_recording = False
        
        if PYAUDIO_AVAILABLE:
            self.audio = pyaudio.PyAudio()
        else:
            self.audio = None
            logger.warning("PyAudio not available - audio recording will be simulated")
        
    def start_recording(self):
        """Start recording audio"""
        if self.is_recording:
            return
        
        self.frames = []
        self.is_recording = True
        
        if PYAUDIO_AVAILABLE and self.audio:
            # Open audio stream
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            logger.info("Started audio recording")
        else:
            logger.info("Started simulated audio recording (PyAudio not available)")
    
    def stop_recording(self) -> bytes:
        """Stop recording and return audio data"""
        if not self.is_recording:
            return b""
        
        self.is_recording = False
        
        if PYAUDIO_AVAILABLE and self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        # Combine all frames
        audio_data = b''.join(self.frames)
        logger.info(f"Stopped recording. Captured {len(audio_data)} bytes")
        
        return audio_data
    
    def record_chunk(self):
        """Record a single chunk of audio"""
        if self.is_recording:
            if PYAUDIO_AVAILABLE and self.stream:
                try:
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    self.frames.append(data)
                except Exception as e:
                    logger.error(f"Error recording audio chunk: {e}")
            else:
                # Simulate audio data when PyAudio is not available
                simulated_data = b'\x00' * (self.chunk_size * 2)  # 2 bytes per sample
                self.frames.append(simulated_data)
    
    def get_audio_level(self) -> float:
        """Get current audio level for visualization"""
        if not self.is_recording or not self.frames:
            return 0.0
        
        if PYAUDIO_AVAILABLE:
            try:
                # Get the last chunk and calculate RMS
                last_chunk = self.frames[-1]
                rms = audioop.rms(last_chunk, 2)  # 2 bytes per sample
                return min(rms / 32768.0, 1.0)  # Normalize to 0-1
            except Exception as e:
                logger.error(f"Error calculating audio level: {e}")
                return 0.0
        else:
            # Return simulated audio level when PyAudio is not available
            return 0.3  # Simulated moderate level
    
    def cleanup(self):
        """Clean up audio resources"""
        if PYAUDIO_AVAILABLE:
            if hasattr(self, 'stream') and self.stream:
                self.stream.close()
            if self.audio:
                self.audio.terminate()

class AudioProcessor:
    """Processes audio files and extracts metadata"""
    
    @staticmethod
    def get_audio_metadata(file_path: str) -> AudioMetadata:
        """Extract metadata from audio file"""
        try:
            with wave.open(file_path, 'rb') as audio_file:
                frames = audio_file.getnframes()
                sample_rate = audio_file.getframerate()
                duration = frames / sample_rate
                channels = audio_file.getnchannels()
                bit_depth = audio_file.getsampwidth() * 8
                
                file_size = os.path.getsize(file_path)
                
                return AudioMetadata(
                    duration_seconds=duration,
                    sample_rate=sample_rate,
                    channels=channels,
                    bit_depth=bit_depth,
                    file_size_bytes=file_size,
                    format="WAV",
                    encoding="PCM"
                )
        except Exception as e:
            logger.error(f"Error extracting audio metadata: {e}")
            return AudioMetadata(
                duration_seconds=0.0,
                sample_rate=16000,
                channels=1,
                bit_depth=16,
                file_size_bytes=0,
                format="UNKNOWN",
                encoding="UNKNOWN"
            )
    
    @staticmethod
    def save_audio_data(audio_data: bytes, file_path: str, sample_rate: int = 16000, 
                       channels: int = 1, bit_depth: int = 16):
        """Save audio data to WAV file"""
        try:
            with wave.open(file_path, 'wb') as audio_file:
                audio_file.setnchannels(channels)
                audio_file.setsampwidth(bit_depth // 8)
                audio_file.setframerate(sample_rate)
                audio_file.writeframes(audio_data)
            
            logger.info(f"Audio saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving audio file: {e}")
            return False
    
    @staticmethod
    def convert_audio_format(input_path: str, output_path: str, target_format: str = "wav"):
        """Convert audio to different format"""
        try:
            # This would use ffmpeg or similar for format conversion
            # For now, we'll just copy the file if it's already WAV
            if input_path.lower().endswith('.wav'):
                import shutil
                shutil.copy2(input_path, output_path)
                return True
            else:
                logger.warning(f"Audio format conversion not implemented for {input_path}")
                return False
        except Exception as e:
            logger.error(f"Error converting audio format: {e}")
            return False

class MockTranscriptionService:
    """Mock transcription service for development"""
    
    def __init__(self):
        self.sample_transcripts = [
            "Build a user authentication system with login and registration",
            "Create an API for managing customer data with CRUD operations",
            "Design a dashboard for monitoring system performance metrics",
            "Implement a workflow engine for processing business rules",
            "Develop a notification system for sending emails and SMS"
        ]
    
    def transcribe_audio(self, audio_file_path: str, language: str = "en") -> TranscriptionResult:
        """Mock transcription of audio file"""
        # Simulate processing time
        time.sleep(1)
        
        # Select a random sample transcript
        import random
        transcript_text = random.choice(self.sample_transcripts)
        
        # Generate mock confidence score
        confidence_score = random.uniform(0.7, 0.95)
        
        # Get audio metadata
        metadata = AudioProcessor.get_audio_metadata(audio_file_path)
        
        return TranscriptionResult(
            transcript_id=str(uuid.uuid4()),
            audio_file_path=audio_file_path,
            transcript_text=transcript_text,
            confidence_score=confidence_score,
            duration_seconds=metadata.duration_seconds,
            language=language,
            metadata={
                "service": "mock_transcription",
                "processing_time": 1.0,
                "audio_metadata": asdict(metadata)
            },
            timestamp=datetime.now()
        )

class VoiceInputProcessor:
    """
    Main voice input processor that handles audio recording, transcription,
    and conversion to structured system instructions
    """
    
    def __init__(self, base_dir: Path, context_engine: ContextEngine):
        self.base_dir = base_dir
        self.context_engine = context_engine
        
        # Audio storage
        self.audio_dir = base_dir / "data" / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.audio_recorder = AudioRecorder()
        self.transcription_service = MockTranscriptionService()  # Mock for development
        
        # In production, this would be:
        # self.transcription_service = WhisperTranscriptionService() or DeepgramTranscriptionService()
        
        logger.info("Voice Input Processor initialized")
    
    def record_voice_memo(self, duration_seconds: int = 30) -> str:
        """Record a voice memo and return the file path"""
        try:
            # Start recording
            self.audio_recorder.start_recording()
            
            # Record for specified duration
            start_time = time.time()
            while time.time() - start_time < duration_seconds:
                self.audio_recorder.record_chunk()
                time.sleep(0.1)  # Small delay to prevent blocking
            
            # Stop recording
            audio_data = self.audio_recorder.stop_recording()
            
            if not audio_data:
                raise Exception("No audio data captured")
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"voice_memo_{timestamp}.wav"
            file_path = self.audio_dir / filename
            
            success = AudioProcessor.save_audio_data(audio_data, str(file_path))
            
            if success:
                logger.info(f"Voice memo saved: {file_path}")
                return str(file_path)
            else:
                raise Exception("Failed to save audio file")
                
        except Exception as e:
            logger.error(f"Error recording voice memo: {e}")
            raise
    
    def process_audio_file(self, audio_file_path: str, user_id: Optional[str] = None,
                          session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process an audio file and convert to structured prompt"""
        
        try:
            # Step 1: Transcribe audio
            transcription_result = self.transcription_service.transcribe_audio(audio_file_path)
            
            # Step 2: Store transcript
            voice_transcript = VoiceTranscript(
                transcript_id=transcription_result.transcript_id,
                audio_file_path=audio_file_path,
                transcript_text=transcription_result.transcript_text,
                confidence_score=transcription_result.confidence_score,
                duration_seconds=transcription_result.duration_seconds,
                prompt_id=None,  # Will be set after prompt processing
                timestamp=transcription_result.timestamp,
                metadata=transcription_result.metadata
            )
            
            # Step 3: Process transcript through context engine
            prompt_result = self.context_engine.process_prompt(
                prompt=transcription_result.transcript_text,
                prompt_type=PromptType.VOICE_MEMO,
                user_id=user_id,
                session_id=session_id
            )
            
            # Step 4: Update transcript with prompt ID
            voice_transcript.prompt_id = prompt_result["prompt_score"]["prompt_id"]
            
            # Step 5: Store transcript in database
            self._store_voice_transcript(voice_transcript)
            
            return {
                "transcript": asdict(voice_transcript),
                "prompt_analysis": prompt_result,
                "audio_metadata": AudioProcessor.get_audio_metadata(audio_file_path)
            }
            
        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            raise
    
    def process_voice_memo(self, user_id: Optional[str] = None,
                          session_id: Optional[str] = None) -> Dict[str, Any]:
        """Record and process a voice memo"""
        
        try:
            # Record voice memo
            audio_file_path = self.record_voice_memo()
            
            # Process the recorded audio
            return self.process_audio_file(audio_file_path, user_id, session_id)
            
        except Exception as e:
            logger.error(f"Error processing voice memo: {e}")
            raise
    
    def get_audio_level(self) -> float:
        """Get current audio level for real-time visualization"""
        return self.audio_recorder.get_audio_level()
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.audio_recorder.is_recording
    
    def _store_voice_transcript(self, voice_transcript: VoiceTranscript):
        """Store voice transcript in database"""
        try:
            with self.context_engine.db_path.parent / "context_engine.db" as db_path:
                import sqlite3
                with sqlite3.connect(db_path) as conn:
                    conn.execute("""
                        INSERT INTO voice_transcripts 
                        (transcript_id, audio_file_path, transcript_text, confidence_score,
                         duration_seconds, prompt_id, timestamp, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        voice_transcript.transcript_id,
                        voice_transcript.audio_file_path,
                        voice_transcript.transcript_text,
                        voice_transcript.confidence_score,
                        voice_transcript.duration_seconds,
                        voice_transcript.prompt_id,
                        voice_transcript.timestamp.isoformat(),
                        json.dumps(voice_transcript.metadata)
                    ))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error storing voice transcript: {e}")
    
    def get_voice_history(self, user_id: Optional[str] = None, 
                         session_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get voice processing history"""
        try:
            # This would query the voice_transcripts table
            # For now, return mock data
            return [
                {
                    "transcript_id": str(uuid.uuid4()),
                    "audio_file_path": "/path/to/audio.wav",
                    "transcript_text": "Build a user authentication system",
                    "confidence_score": 0.85,
                    "duration_seconds": 15.5,
                    "timestamp": datetime.now().isoformat(),
                    "prompt_score": 0.75
                }
            ]
        except Exception as e:
            logger.error(f"Error getting voice history: {e}")
            return []
    
    def cleanup(self):
        """Clean up resources"""
        self.audio_recorder.cleanup()

# Production-ready transcription services (commented out for development)

class WhisperTranscriptionService:
    """OpenAI Whisper transcription service"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Initialize Whisper client
    
    def transcribe_audio(self, audio_file_path: str, language: str = "en") -> TranscriptionResult:
        """Transcribe audio using OpenAI Whisper"""
        # Implementation would use OpenAI Whisper API
        pass

class DeepgramTranscriptionService:
    """Deepgram transcription service"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Initialize Deepgram client
    
    def transcribe_audio(self, audio_file_path: str, language: str = "en") -> TranscriptionResult:
        """Transcribe audio using Deepgram"""
        # Implementation would use Deepgram API
        pass
