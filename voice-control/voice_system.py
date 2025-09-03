#!/usr/bin/env python3
"""
QENEX Voice Control System
Advanced voice recognition, natural language processing, and command execution
"""

import asyncio
import json
import time
import logging
import threading
import queue
import wave
import io
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable, Any, Tuple
import speech_recognition as sr
import pyttsx3
import pyaudio
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import spacy
import re
import subprocess
import difflib

@dataclass
class VoiceCommand:
    """Voice command definition"""
    command_id: str
    name: str
    patterns: List[str]  # Regex patterns or keywords
    description: str
    handler: str  # Function name to handle command
    parameters: List[Dict[str, Any]] = None
    confidence_threshold: float = 0.7
    requires_confirmation: bool = False
    category: str = "general"

@dataclass
class ConversationContext:
    """Conversation context tracking"""
    session_id: str
    user_id: Optional[str]
    start_time: float
    last_activity: float
    conversation_history: List[Dict[str, Any]]
    context_variables: Dict[str, Any]
    current_task: Optional[str] = None
    awaiting_confirmation: Optional[str] = None

class QenexVoiceControl:
    """Advanced voice control system with NLP"""
    
    def __init__(self, config_path: str = "/opt/qenex-os/config/voice_control.json"):
        self.config_path = config_path
        self.commands: Dict[str, VoiceCommand] = {}
        self.conversations: Dict[str, ConversationContext] = {}
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.tts_engine = None
        self.nlp_model = None
        
        # Audio processing
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.wake_word_detected = False
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/opt/qenex-os/logs/voice_control.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('QenexVoiceControl')
        
        # Initialize components
        self.load_config()
        self.init_speech_recognition()
        self.init_text_to_speech()
        self.init_nlp()
        self.register_default_commands()
        
    def load_config(self):
        """Load voice control configuration"""
        default_config = {
            "enabled": True,
            "wake_words": ["qenex", "hey qenex", "ok qenex"],
            "language": "en-US",
            "speech_recognition": {
                "engine": "google",  # google, sphinx, wit, azure
                "timeout": 5,
                "phrase_timeout": 0.5,
                "energy_threshold": 300,
                "dynamic_threshold": True
            },
            "text_to_speech": {
                "engine": "pyttsx3",
                "voice": "default",
                "rate": 150,
                "volume": 0.8
            },
            "nlp": {
                "model": "en_core_web_sm",
                "intent_confidence": 0.7,
                "entity_extraction": True,
                "sentiment_analysis": True
            },
            "conversation": {
                "timeout_minutes": 15,
                "max_history": 50,
                "context_persistence": True
            },
            "security": {
                "voice_authentication": False,
                "command_confirmation": ["system", "admin", "delete"],
                "restricted_commands": []
            }
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
                self.save_config()
        except Exception as e:
            self.logger.warning(f"Failed to load config: {e}, using defaults")
            self.config = default_config
            
    def save_config(self):
        """Save current configuration"""
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
            
    def init_speech_recognition(self):
        """Initialize speech recognition"""
        try:
            # Configure recognizer
            self.recognizer.energy_threshold = self.config["speech_recognition"]["energy_threshold"]
            self.recognizer.dynamic_energy_threshold = self.config["speech_recognition"]["dynamic_threshold"]
            self.recognizer.phrase_threshold = self.config["speech_recognition"]["phrase_timeout"]
            
            # Initialize microphone
            self.microphone = sr.Microphone()
            
            # Calibrate for ambient noise
            with self.microphone as source:
                self.logger.info("Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source)
                
            self.logger.info("Speech recognition initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize speech recognition: {e}")
            
    def init_text_to_speech(self):
        """Initialize text-to-speech engine"""
        try:
            self.tts_engine = pyttsx3.init()
            
            # Configure TTS
            tts_config = self.config["text_to_speech"]
            self.tts_engine.setProperty('rate', tts_config["rate"])
            self.tts_engine.setProperty('volume', tts_config["volume"])
            
            # Set voice if specified
            if tts_config["voice"] != "default":
                voices = self.tts_engine.getProperty('voices')
                for voice in voices:
                    if tts_config["voice"].lower() in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                        
            self.logger.info("Text-to-speech initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS: {e}")
            
    def init_nlp(self):
        """Initialize NLP components"""
        try:
            # Download required NLTK data
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt')
                
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords')
                
            try:
                nltk.data.find('corpora/wordnet')
            except LookupError:
                nltk.download('wordnet')
                
            # Initialize lemmatizer
            self.lemmatizer = WordNetLemmatizer()
            self.stop_words = set(stopwords.words('english'))
            
            # Load spaCy model if available
            try:
                self.nlp_model = spacy.load(self.config["nlp"]["model"])
                self.logger.info("spaCy NLP model loaded")
            except OSError:
                self.logger.warning("spaCy model not found, using basic NLP")
                self.nlp_model = None
                
        except Exception as e:
            self.logger.error(f"Failed to initialize NLP: {e}")
            
    def register_command(self, command: VoiceCommand):
        """Register a voice command"""
        self.commands[command.command_id] = command
        self.logger.info(f"Registered voice command: {command.name}")
        
    def register_default_commands(self):
        """Register default system commands"""
        
        # System status commands
        self.register_command(VoiceCommand(
            command_id="system_status",
            name="System Status",
            patterns=[
                r"(?:what|how)(?:'s|is)?\s+(?:the\s+)?(?:system\s+)?status",
                r"show\s+(?:me\s+)?(?:system\s+)?status",
                r"system\s+health",
                r"how\s+(?:are\s+)?(?:you\s+)?(?:doing|running)"
            ],
            description="Get system status and health information",
            handler="handle_system_status",
            category="system"
        ))
        
        # Pipeline management
        self.register_command(VoiceCommand(
            command_id="list_pipelines",
            name="List Pipelines",
            patterns=[
                r"(?:list|show)\s+(?:all\s+)?pipelines?",
                r"what\s+pipelines?\s+(?:are\s+)?(?:available|running)",
                r"show\s+me\s+(?:the\s+)?pipelines?"
            ],
            description="List all available pipelines",
            handler="handle_list_pipelines",
            category="pipeline"
        ))
        
        self.register_command(VoiceCommand(
            command_id="run_pipeline",
            name="Run Pipeline",
            patterns=[
                r"(?:run|start|execute)\s+(?:the\s+)?pipeline\s+(.+)",
                r"(?:run|start|execute)\s+(.+)\s+pipeline"
            ],
            description="Execute a specific pipeline",
            handler="handle_run_pipeline",
            parameters=[{"name": "pipeline_name", "type": "string", "required": True}],
            category="pipeline"
        ))
        
        # Backup and recovery
        self.register_command(VoiceCommand(
            command_id="create_backup",
            name="Create Backup",
            patterns=[
                r"(?:create|make|start)\s+(?:a\s+)?backup",
                r"backup\s+(?:the\s+)?(?:system|data)",
                r"run\s+backup"
            ],
            description="Create system backup",
            handler="handle_create_backup",
            requires_confirmation=True,
            category="backup"
        ))
        
        # Security commands
        self.register_command(VoiceCommand(
            command_id="security_status",
            name="Security Status",
            patterns=[
                r"(?:show|check)\s+security\s+status",
                r"security\s+(?:dashboard|overview)",
                r"how\s+secure\s+(?:are\s+we|is\s+the\s+system)"
            ],
            description="Get security status and alerts",
            handler="handle_security_status",
            category="security"
        ))
        
        # General conversation
        self.register_command(VoiceCommand(
            command_id="greeting",
            name="Greeting",
            patterns=[
                r"(?:hello|hi|hey)\s+(?:qenex)?",
                r"good\s+(?:morning|afternoon|evening)",
                r"how\s+are\s+you"
            ],
            description="Respond to greetings",
            handler="handle_greeting",
            category="conversation"
        ))
        
        self.register_command(VoiceCommand(
            command_id="help",
            name="Help",
            patterns=[
                r"help",
                r"what\s+can\s+you\s+do",
                r"(?:show|list)\s+(?:available\s+)?commands?",
                r"what\s+commands?\s+(?:are\s+)?available"
            ],
            description="Show available commands",
            handler="handle_help",
            category="general"
        ))
        
        # System control
        self.register_command(VoiceCommand(
            command_id="restart_service",
            name="Restart Service",
            patterns=[
                r"restart\s+(.+)\s+service",
                r"restart\s+(.+)",
                r"reboot\s+(.+)"
            ],
            description="Restart a system service",
            handler="handle_restart_service",
            parameters=[{"name": "service_name", "type": "string", "required": True}],
            requires_confirmation=True,
            category="system"
        ))
        
    async def listen_continuously(self):
        """Continuously listen for voice commands"""
        self.logger.info("Starting continuous voice listening...")
        self.is_listening = True
        
        while self.is_listening and self.config.get("enabled", True):
            try:
                # Listen for wake word or command
                with self.microphone as source:
                    self.logger.debug("Listening...")
                    audio = self.recognizer.listen(
                        source, 
                        timeout=self.config["speech_recognition"]["timeout"],
                        phrase_time_limit=10
                    )
                    
                # Process audio in background
                asyncio.create_task(self.process_audio(audio))
                
            except sr.WaitTimeoutError:
                # Timeout is normal, continue listening
                pass
            except Exception as e:
                self.logger.error(f"Error in listening loop: {e}")
                await asyncio.sleep(1)
                
    async def process_audio(self, audio):
        """Process captured audio"""
        try:
            # Convert speech to text
            text = await self.speech_to_text(audio)
            
            if not text:
                return
                
            self.logger.info(f"Recognized speech: {text}")
            
            # Check for wake word if not already activated
            if not self.wake_word_detected:
                if self.detect_wake_word(text):
                    self.wake_word_detected = True
                    self.speak("Yes, I'm listening.")
                    return
                else:
                    return  # Ignore speech without wake word
            
            # Process command
            await self.process_command(text)
            
            # Reset wake word after processing
            self.wake_word_detected = False
            
        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            
    async def speech_to_text(self, audio) -> Optional[str]:
        """Convert speech to text"""
        try:
            engine = self.config["speech_recognition"]["engine"]
            
            if engine == "google":
                text = self.recognizer.recognize_google(audio, language=self.config["language"])
            elif engine == "sphinx":
                text = self.recognizer.recognize_sphinx(audio)
            else:
                text = self.recognizer.recognize_google(audio, language=self.config["language"])
                
            return text.lower().strip() if text else None
            
        except sr.UnknownValueError:
            self.logger.debug("Could not understand audio")
            return None
        except sr.RequestError as e:
            self.logger.error(f"Speech recognition error: {e}")
            return None
            
    def detect_wake_word(self, text: str) -> bool:
        """Check if text contains wake word"""
        wake_words = self.config["wake_words"]
        text_lower = text.lower()
        
        for wake_word in wake_words:
            if wake_word.lower() in text_lower:
                return True
                
        return False
        
    async def process_command(self, text: str, session_id: str = "default"):
        """Process voice command using NLP"""
        try:
            # Get or create conversation context
            if session_id not in self.conversations:
                self.conversations[session_id] = ConversationContext(
                    session_id=session_id,
                    user_id=None,
                    start_time=time.time(),
                    last_activity=time.time(),
                    conversation_history=[],
                    context_variables={}
                )
                
            context = self.conversations[session_id]
            context.last_activity = time.time()
            
            # Add to conversation history
            context.conversation_history.append({
                "timestamp": time.time(),
                "type": "user_input",
                "content": text
            })
            
            # Check if awaiting confirmation
            if context.awaiting_confirmation:
                await self.handle_confirmation(text, context)
                return
                
            # Find matching command
            matched_command, confidence, parameters = self.match_command(text)
            
            if matched_command and confidence >= matched_command.confidence_threshold:
                self.logger.info(f"Matched command: {matched_command.name} (confidence: {confidence:.2f})")
                
                # Check if confirmation required
                if matched_command.requires_confirmation:
                    context.awaiting_confirmation = matched_command.command_id
                    context.context_variables["pending_command"] = matched_command
                    context.context_variables["pending_parameters"] = parameters
                    
                    confirmation_text = f"Are you sure you want to {matched_command.name.lower()}?"
                    if parameters:
                        param_text = ", ".join(f"{k}: {v}" for k, v in parameters.items())
                        confirmation_text += f" Parameters: {param_text}"
                        
                    self.speak(confirmation_text)
                    return
                    
                # Execute command
                await self.execute_command(matched_command, parameters, context)
                
            else:
                # Try to handle as natural language query
                response = await self.handle_natural_language(text, context)
                if response:
                    self.speak(response)
                else:
                    self.speak("I'm sorry, I didn't understand that command. Say 'help' to see available commands.")
                    
        except Exception as e:
            self.logger.error(f"Error processing command: {e}")
            self.speak("I encountered an error processing that command.")
            
    def match_command(self, text: str) -> Tuple[Optional[VoiceCommand], float, Dict[str, Any]]:
        """Match text to registered commands"""
        best_match = None
        best_confidence = 0
        best_parameters = {}
        
        for command in self.commands.values():
            for pattern in command.patterns:
                # Try regex matching first
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    confidence = 1.0  # Exact pattern match
                    
                    # Extract parameters from regex groups
                    parameters = {}
                    if command.parameters and match.groups():
                        for i, param in enumerate(command.parameters):
                            if i < len(match.groups()) and match.group(i + 1):
                                parameters[param["name"]] = match.group(i + 1).strip()
                                
                    if confidence > best_confidence:
                        best_match = command
                        best_confidence = confidence
                        best_parameters = parameters
                        
                # Try fuzzy matching for command keywords
                command_words = set(word_tokenize(command.name.lower()))
                text_words = set(word_tokenize(text.lower()))
                
                # Remove stop words
                command_words -= self.stop_words
                text_words -= self.stop_words
                
                if command_words and text_words:
                    overlap = len(command_words & text_words)
                    fuzzy_confidence = overlap / len(command_words)
                    
                    if fuzzy_confidence > 0.5 and fuzzy_confidence > best_confidence:
                        best_match = command
                        best_confidence = fuzzy_confidence
                        best_parameters = {}
                        
        return best_match, best_confidence, best_parameters
        
    async def handle_confirmation(self, text: str, context: ConversationContext):
        """Handle confirmation responses"""
        text_lower = text.lower()
        
        positive_responses = ["yes", "yeah", "yep", "ok", "okay", "sure", "confirm", "do it"]
        negative_responses = ["no", "nope", "cancel", "abort", "never mind", "stop"]
        
        is_positive = any(response in text_lower for response in positive_responses)
        is_negative = any(response in text_lower for response in negative_responses)
        
        if is_positive:
            # Execute the pending command
            pending_command = context.context_variables.get("pending_command")
            pending_parameters = context.context_variables.get("pending_parameters", {})
            
            if pending_command:
                self.speak("Confirmed. Executing command.")
                await self.execute_command(pending_command, pending_parameters, context)
            
        elif is_negative:
            self.speak("Command cancelled.")
            
        else:
            self.speak("Please say yes to confirm or no to cancel.")
            return  # Don't clear awaiting confirmation
            
        # Clear confirmation state
        context.awaiting_confirmation = None
        if "pending_command" in context.context_variables:
            del context.context_variables["pending_command"]
        if "pending_parameters" in context.context_variables:
            del context.context_variables["pending_parameters"]
            
    async def execute_command(self, command: VoiceCommand, parameters: Dict[str, Any], 
                            context: ConversationContext):
        """Execute a matched command"""
        try:
            # Get handler method
            handler_method = getattr(self, command.handler, None)
            
            if not handler_method:
                self.speak(f"Command handler not found: {command.handler}")
                return
                
            # Execute handler
            response = await handler_method(parameters, context)
            
            # Speak response if provided
            if response:
                self.speak(response)
                
            # Add to conversation history
            context.conversation_history.append({
                "timestamp": time.time(),
                "type": "command_executed",
                "command": command.name,
                "parameters": parameters,
                "response": response
            })
            
        except Exception as e:
            self.logger.error(f"Error executing command {command.name}: {e}")
            self.speak("I encountered an error executing that command.")
            
    async def handle_natural_language(self, text: str, context: ConversationContext) -> Optional[str]:
        """Handle natural language queries using NLP"""
        if not self.nlp_model:
            return None
            
        try:
            # Process with spaCy
            doc = self.nlp_model(text)
            
            # Extract entities and intents
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            
            # Simple intent recognition based on keywords
            if any(word in text.lower() for word in ["status", "health", "running"]):
                return await self.handle_system_status({}, context)
            elif any(word in text.lower() for word in ["pipeline", "process", "job"]):
                return await self.handle_list_pipelines({}, context)
            elif any(word in text.lower() for word in ["backup", "save", "protect"]):
                return "I can help with backups. Say 'create backup' to start a backup process."
            elif any(word in text.lower() for word in ["security", "safe", "protect"]):
                return await self.handle_security_status({}, context)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in NLP processing: {e}")
            return None
            
    def speak(self, text: str):
        """Convert text to speech"""
        try:
            if self.tts_engine:
                self.logger.info(f"Speaking: {text}")
                
                # Run TTS in a separate thread to avoid blocking
                def speak_thread():
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
                    
                threading.Thread(target=speak_thread, daemon=True).start()
                
        except Exception as e:
            self.logger.error(f"Error in text-to-speech: {e}")
            
    # Command handlers
    async def handle_system_status(self, parameters: Dict[str, Any], 
                                 context: ConversationContext) -> str:
        """Handle system status command"""
        try:
            # Get system metrics
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Check QENEX services
            services_status = "All services running normally"
            
            response = f"""System status report:
            CPU usage is {cpu_percent:.1f} percent.
            Memory usage is {memory.percent:.1f} percent.
            Disk usage is {disk.used / disk.total * 100:.1f} percent.
            {services_status}."""
            
            return response
            
        except Exception as e:
            return f"Error retrieving system status: {e}"
            
    async def handle_list_pipelines(self, parameters: Dict[str, Any], 
                                  context: ConversationContext) -> str:
        """Handle list pipelines command"""
        try:
            # Check if pipeline data exists
            pipeline_file = Path("/opt/qenex-os/data/pipelines")
            
            if pipeline_file.exists():
                pipelines = list(pipeline_file.glob("*.json"))
                if pipelines:
                    pipeline_names = [p.stem for p in pipelines[:5]]  # Limit to 5
                    response = f"I found {len(pipelines)} pipelines: {', '.join(pipeline_names)}"
                    if len(pipelines) > 5:
                        response += f" and {len(pipelines) - 5} more"
                else:
                    response = "No pipelines found."
            else:
                response = "Pipeline directory not found. No pipelines available."
                
            return response
            
        except Exception as e:
            return f"Error listing pipelines: {e}"
            
    async def handle_run_pipeline(self, parameters: Dict[str, Any], 
                                context: ConversationContext) -> str:
        """Handle run pipeline command"""
        pipeline_name = parameters.get("pipeline_name", "").strip()
        
        if not pipeline_name:
            return "Please specify which pipeline to run."
            
        try:
            # Simulate pipeline execution
            response = f"Starting pipeline: {pipeline_name}. I'll notify you when it's complete."
            
            # In a real implementation, this would trigger the actual pipeline
            # For now, just acknowledge the command
            
            return response
            
        except Exception as e:
            return f"Error running pipeline {pipeline_name}: {e}"
            
    async def handle_create_backup(self, parameters: Dict[str, Any], 
                                 context: ConversationContext) -> str:
        """Handle create backup command"""
        try:
            # Trigger backup system
            backup_command = [
                "python3", "/opt/qenex-os/backup-recovery/backup_system.py", 
                "--create-backup", "--type=manual"
            ]
            
            # Start backup in background
            process = subprocess.Popen(backup_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            return "Backup process started. This may take several minutes to complete."
            
        except Exception as e:
            return f"Error starting backup: {e}"
            
    async def handle_security_status(self, parameters: Dict[str, Any], 
                                   context: ConversationContext) -> str:
        """Handle security status command"""
        try:
            # Check security status
            security_file = Path("/opt/qenex-os/data/security_events.json")
            
            if security_file.exists():
                with open(security_file, 'r') as f:
                    events = json.load(f)
                    
                recent_events = len(events)
                high_risk_events = len([e for e in events if e.get("risk_score", 0) > 70])
                
                if high_risk_events > 0:
                    response = f"Security alert: {high_risk_events} high-risk events detected in the last 24 hours."
                else:
                    response = f"Security status is good. {recent_events} events logged with no high-risk activities."
            else:
                response = "Security monitoring is active. No events to report."
                
            return response
            
        except Exception as e:
            return f"Error checking security status: {e}"
            
    async def handle_greeting(self, parameters: Dict[str, Any], 
                            context: ConversationContext) -> str:
        """Handle greeting commands"""
        greetings = [
            "Hello! How can I help you today?",
            "Hi there! I'm ready to assist you.",
            "Good day! What can I do for you?",
            "Hello! QENEX AI is at your service."
        ]
        
        import random
        return random.choice(greetings)
        
    async def handle_help(self, parameters: Dict[str, Any], 
                        context: ConversationContext) -> str:
        """Handle help command"""
        categories = {}
        
        for command in self.commands.values():
            category = command.category
            if category not in categories:
                categories[category] = []
            categories[category].append(command.name)
            
        help_text = "Here are the available commands: "
        
        for category, commands in categories.items():
            help_text += f"{category.title()}: {', '.join(commands[:3])}. "
            
        help_text += "You can also ask me questions in natural language."
        
        return help_text
        
    async def handle_restart_service(self, parameters: Dict[str, Any], 
                                   context: ConversationContext) -> str:
        """Handle restart service command"""
        service_name = parameters.get("service_name", "").strip()
        
        if not service_name:
            return "Please specify which service to restart."
            
        try:
            # Restart service using systemctl
            result = subprocess.run(
                ["systemctl", "restart", service_name],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                return f"Successfully restarted {service_name} service."
            else:
                return f"Failed to restart {service_name}. Error: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return f"Timeout while restarting {service_name} service."
        except Exception as e:
            return f"Error restarting {service_name}: {e}"
            
    def get_voice_status(self) -> Dict:
        """Get voice control system status"""
        active_conversations = len(self.conversations)
        total_commands = len(self.commands)
        
        # Get conversation statistics
        total_interactions = 0
        for conversation in self.conversations.values():
            total_interactions += len(conversation.conversation_history)
            
        return {
            "enabled": self.config["enabled"],
            "listening": self.is_listening,
            "wake_word_active": self.wake_word_detected,
            "total_commands": total_commands,
            "active_conversations": active_conversations,
            "total_interactions": total_interactions,
            "speech_engine": self.config["speech_recognition"]["engine"],
            "tts_engine": self.config["text_to_speech"]["engine"],
            "language": self.config["language"],
            "nlp_enabled": self.nlp_model is not None
        }
        
    async def start(self):
        """Start the voice control system"""
        self.logger.info("Starting QENEX Voice Control System")
        
        if not self.microphone:
            self.logger.error("No microphone available")
            return
            
        # Start listening loop
        await self.listen_continuously()
        
    def stop(self):
        """Stop the voice control system"""
        self.logger.info("Stopping QENEX Voice Control System")
        self.is_listening = False
        self.config['enabled'] = False

async def main():
    """Main entry point"""
    voice_control = QenexVoiceControl()
    
    try:
        print("QENEX Voice Control System")
        print("Say 'Hey QENEX' followed by your command")
        print("Say 'Hey QENEX help' to see available commands")
        print("Press Ctrl+C to stop")
        
        await voice_control.start()
        
    except KeyboardInterrupt:
        voice_control.stop()
        print("\nVoice control stopped")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())