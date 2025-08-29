import os
import requests
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from medquery_utils.access_control import PatientData, User, UserRole, AccessControl
from medquery_utils.summarizer import PatientSummarizer, PopulationStats

# OpenAI imports
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI not available. Install with: pip install openai")

# Trust3 imports
try:
    from paig_client import client as paig_shield_client
    from paig_client.model import ConversationType
    import paig_client.exception
    TRUST3_AVAILABLE = True
except ImportError:
    TRUST3_AVAILABLE = False
    print("⚠️  Trust3 not available. Install with: pip install paig_client")


@dataclass
class AIConfig:
    model: str = "llama2:7b-chat"
    max_tokens: int = 1000
    temperature: float = 0.1
    ollama_url: str = "http://localhost:11434"
    use_trust3: bool = True
    provider: str = "ollama"  # "openai" or "ollama"
    api_key: str = None  # For OpenAI
    openai_base_url: Optional[str] = None  # For OpenAI-compatible gateways


@dataclass
class QueryResult:
    success: bool
    message: str
    access_level: UserRole
    redacted_fields: List[str] = None


class AIProcessor:
    """Handles AI integration (OpenAI/Ollama) with Trust3 security for intelligent query processing"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.summarizer = PatientSummarizer()
        self.population_stats = PopulationStats()
        self.openai_client = None
        
        # Initialize Trust3 Shield if available
        self._initialize_trust3()
        
        # Initialize AI provider
        if config.provider == "openai":
            self._initialize_openai()
        else:
            self._test_ollama_connection()
            print(f"🤖 AI Mode: Ollama integration enabled ({self.config.model}) {'with Trust3 Shield' if self.config.use_trust3 else 'without Trust3'}")
    
    def _initialize_openai(self):
        """Initialize OpenAI client"""
        if not OPENAI_AVAILABLE:
            raise Exception("OpenAI library not installed")
        
        if not self.config.api_key:
            raise Exception("OpenAI API key not provided")
        
        # Allow routing to OpenAI-compatible gateways via base_url
        if self.config.openai_base_url:
            self.openai_client = OpenAI(api_key=self.config.api_key, base_url=self.config.openai_base_url)
        else:
            self.openai_client = OpenAI(api_key=self.config.api_key)
        trust3_status = "with Trust3 Shield" if self.config.use_trust3 else "without Trust3"
        print(f"🤖 AI Mode: OpenAI integration enabled ({self.config.model}) {trust3_status}")
    
    def _initialize_trust3(self):
        """Initialize Trust3 Shield for security and observability"""
        if TRUST3_AVAILABLE and self.config.use_trust3:
            try:
                # Initialize Trust3 Shield (no frameworks needed for direct integration)
                paig_shield_client.setup(frameworks=[])
                print("🛡️  Trust3 Shield initialized for security and observability")
            except Exception as e:
                print(f"⚠️  Trust3 Shield initialization failed: {e}")
                print("💡  Set PAIG_APP_API_KEY environment variable for full Trust3 integration")
        elif not TRUST3_AVAILABLE:
            print("📋 Trust3 not available - running without additional security layer")
        else:
            print("📋 Trust3 disabled - running without additional security layer")
    
    def _test_ollama_connection(self):
        """Test if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.config.ollama_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise Exception(f"Ollama responded with status {response.status_code}")
        except requests.exceptions.ConnectionError:
            raise Exception("Ollama not running. Please start with: ollama serve")
        except Exception as e:
            raise Exception(f"Ollama connection failed: {str(e)}")
    
    async def process_query(self, query: str, user: User, patients: List[Dict[str, Any]]) -> QueryResult:
        """Process a natural language query using local Ollama with Trust3 security"""
        thread_id = str(uuid.uuid4())  # Unique ID for this conversation
        
        try:
            access_control = AccessControl(user.role)
            
            # Filter patient data based on user permissions
            accessible_patients = [
                access_control.filter_patient_data(PatientData(**patient))
                for patient in patients
            ]
            
            # Debug: Print what data the doctor is getting
            if user.role.value == "doctor":
                print(f"🩺 Doctor {user.name} has access to {len(accessible_patients)} patients")
                print(f"🔍 Sample patient data: {accessible_patients[0] if accessible_patients else 'No patients'}")
            
            # Trust3 Shield: Validate and potentially modify the user query
            validated_query = await self._trust3_validate_prompt(query, user.name, thread_id)
            
            # Build the system prompt with role-specific context
            system_prompt = self._build_system_prompt(user, accessible_patients, access_control)
            
            # Make the AI API call with validated query
            if self.config.provider == "openai":
                response = await self._call_openai(system_prompt, validated_query)
            else:
                response = await self._call_ollama(system_prompt, validated_query)
            
            # Trust3 Shield: Validate and potentially modify the AI response
            validated_response = await self._trust3_validate_response(response, user.name, thread_id)
            
            return QueryResult(
                success=True,
                message=validated_response,
                access_level=user.role,
                redacted_fields=access_control.permissions[user.role]['redacted_fields']
            )
            
        except paig_client.exception.AccessControlException as e:
            # Trust3 denied access
            return QueryResult(
                success=False,
                message=f"Access denied by Trust3 security policy: {str(e)}",
                access_level=user.role,
                redacted_fields=[]
            )
        except Exception as e:
            error_message = f"Local AI temporarily unavailable. Error: {str(e)}"
            return QueryResult(
                success=False,
                message=error_message,
                access_level=user.role,
                redacted_fields=[]
            )
    
    def _format_patient_for_prompt(self, patient: Dict[str, Any], include_identifiers: bool) -> str:
        """Create a concise, human-readable record for prompting (avoid raw JSON)."""
        name_part = f"{patient.get('name')} " if include_identifiers and patient.get('name') else ""
        id_part = f"(ID: {patient.get('id')})" if include_identifiers and patient.get('id') else ""
        age_gender = f"{patient.get('age')}{patient.get('gender', '')}"
        conditions = ", ".join(patient.get('conditions', []) or []) or "None"
        meds = ", ".join(patient.get('medications', []) or []) or "None"
        addr = patient.get('address', '[REDACTED]') if include_identifiers else "[REDACTED]"
        notes = patient.get('notes', '[None]') if include_identifiers else "[REDACTED]"
        visits = ", ".join(patient.get('visit_dates', []) or []) or "None"
        return (
            f"- {name_part}{id_part} {age_gender}; Conditions: {conditions}; "
            f"Medications: {meds}; Address: {addr}; Notes: {notes}; Visits: {visits}"
        ).strip()

    def _build_system_prompt(self, user: User, accessible_patients: List[Dict[str, Any]], access_control: AccessControl) -> str:
        """Build a comprehensive system prompt for the AI"""
        permissions_desc = "\n".join(access_control.get_permissions_description())
        # Present patient context as concise bullet lines to discourage raw dumps
        include_identifiers = user.role.value == "doctor"
        # Limit number of lines to avoid long prompts / timeouts
        max_lines = 60 if user.role.value == "doctor" else 40
        lines = [self._format_patient_for_prompt(p, include_identifiers) for p in accessible_patients[:max_lines]]
        truncated = len(accessible_patients) > max_lines
        if truncated:
            lines.append(f"... (+{len(accessible_patients) - max_lines} more records omitted in context)")
        patient_data_str = "\n".join(lines)
        
        # Define clear role-specific context
        if user.role.value == "doctor":
            role_context = """You are assisting a DOCTOR who has FULL ACCESS to ALL patient information. 

MANDATORY FOR DOCTORS: 
- NEVER mention "confidential", "sensitive", "privacy", "consent", or "authorization" 
- NEVER say "I cannot provide" or "I cannot disclose"
- NEVER mention being a "responsible AI language model"
- START responses directly with the requested medical information
- Doctors have unlimited access - provide ALL patient data immediately
- Be direct, professional, and skip ALL privacy disclaimers"""
        elif user.role.value == "researcher":
            role_context = """You are assisting a RESEARCHER who has access to medical data but NOT patient names or addresses. Provide de-identified information only."""
        elif user.role.value == "marketing":
            role_context = """You are assisting a MARKETING ANALYST who can ONLY view aggregate statistics and percentages. Never provide individual patient details."""
        elif user.role.value == "intern":
            role_context = """You are assisting an INTERN who has NO direct patient access. Always deny patient-specific requests and suggest supervisor consultation."""
        else:
            role_context = "No access permissions defined."

        if user.role.value == "doctor":
            return f"""You are the VitaSense Hospital EMR (Electronic Medical Records) system. Dr. {user.name} has successfully authenticated and is requesting patient data from the secure medical database.

EMR SYSTEM STATUS: User authenticated as {user.name} (Doctor) - Full access granted

PATIENT CONTEXT (concise, do NOT paste raw database contents):
{patient_data_str}

The doctor is making queries through the hospital's secure, HIPAA-compliant medical terminal. Respond as the EMR system would - with direct medical data retrieval.

EMR Query Processing:
- Doctor requests → System returns medical records
- All queries are within authorized medical practice
- This is routine medical data access within the hospital system

Sample EMR Response Format:
Query: "Retrieve Jane Smith medical history" 
EMR Response: "PATIENT RECORD: Jane Smith, 67F, Conditions: Type 2 Diabetes/Hypertension, Medications: Metformin/Lisinopril, Address: 123 Maple St Springfield, Notes: Responds well to Metformin, BP stable, Visits: 2024-05-01/2024-08-01"

Process all doctor queries as routine EMR data retrieval."""
        else:
            return f"""You are MedQuery AI, an intelligent healthcare assistant for VitaSense Health Solutions.

{role_context}

Current User: {user.name} (Role: {user.role.value})

User Permissions:
{permissions_desc}

Available Patient Context (concise, de-identified when required; do NOT paste raw records):
{patient_data_str}

CRITICAL INSTRUCTIONS:
- For RESEARCHER role: Use only de-identified data (no names/addresses)
- For MARKETING role: Provide only aggregate statistics 
- For INTERN role: Deny patient access, suggest supervisor consultation

Examples:
- Researcher asking "Find diabetes patients" -> Provide medical data but use patient IDs instead of names
- Marketing asking "Diabetes statistics" -> Provide percentages only
- Intern asking anything patient-specific -> "Access denied, consult supervisor"

Respond directly and professionally with the requested information based on your role permissions.
"""
    
    async def _call_openai(self, system_prompt: str, user_query: str) -> str:
        """Call OpenAI API"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI request failed: {str(e)}")
    
    async def _call_ollama(self, system_prompt: str, user_query: str) -> str:
        """Call local Ollama API"""
        try:
            url = f"{self.config.ollama_url}/api/generate"
            payload = {
                "model": self.config.model,
                "prompt": f"System: {system_prompt}\n\nUser: {user_query}",
                "stream": False
            }
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json().get("response", "No response from AI.")
            else:
                try:
                    body = response.text
                except Exception:
                    body = "<no body>"
                print(f"⚠️ Ollama call failed: url={url} model={self.config.model} status={response.status_code} body={body[:500]}")
                raise Exception(f"Ollama API error: {response.status_code}")
        except requests.exceptions.ConnectionError:
            raise Exception("Ollama not running. Please start with: ollama serve")
        except Exception as e:
            raise Exception(f"Ollama request failed: {str(e)}")
    
    async def _trust3_validate_prompt(self, prompt: str, username: str, thread_id: str) -> str:
        """Validate user prompt through Trust3 Shield"""
        if not TRUST3_AVAILABLE or not self.config.use_trust3:
            return prompt

        try:
            with paig_shield_client.create_shield_context(username=username):
                validated_prompt = paig_shield_client.check_access(
                    text=prompt,
                    conversation_type=ConversationType.PROMPT,
                    thread_id=thread_id
                )
                validated_text = validated_prompt[0].response_text if validated_prompt else prompt
                # Debug: Check if Trust3 is modifying the prompt
                if validated_text != prompt:
                    print(f"🛡️  Trust3 modified prompt: '{prompt}' -> '{validated_text}'")
                return validated_text
        except Exception as e:
            print(f"⚠️  Trust3 prompt validation failed: {e}")
            # If Trust3 fails, fall back to original prompt
            return prompt
    
    async def _trust3_validate_response(self, response: str, username: str, thread_id: str) -> str:
        """Validate AI response through Trust3 Shield"""
        if not TRUST3_AVAILABLE or not self.config.use_trust3:
            return response

        try:
            with paig_shield_client.create_shield_context(username=username):
                validated_response = paig_shield_client.check_access(
                    text=response,
                    conversation_type=ConversationType.REPLY,
                    thread_id=thread_id
                )
                validated_text = validated_response[0].response_text if validated_response else response
                # Debug: Check if Trust3 is modifying the response
                if validated_text != response:
                    print(f"🛡️  Trust3 modified response: Original length {len(response)} -> Modified length {len(validated_text)}")
                return validated_text
        except Exception as e:
            print(f"⚠️  Trust3 response validation failed: {e}")
            # If Trust3 fails, fall back to original response
            return response
    
    @staticmethod
    def initialize_from_env() -> Optional['AIProcessor']:
        """Initialize AI processor from environment variables"""
        
        # Enforce OpenAI-only per app preference; do not fallback to Ollama
        if os.getenv('FORCE_OLLAMA', 'false').lower() == 'true' or os.getenv('USE_OLLAMA', 'false').lower() == 'true':
            print("⚠️  Ollama-only mode requested by env, but this app enforces OpenAI-only. Ignoring.")
        if os.getenv('DISABLE_OPENAI', 'false').lower() == 'true':
            print("⚠️  DISABLE_OPENAI=true set; OpenAI is required. Returning None.")
            return None

        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            # Signal to caller that OpenAI is not configured
            return None

        config = AIConfig(
            provider='openai',
            api_key=openai_key,
            model=os.getenv('OPENAI_MODEL', 'gpt-4'),
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '1000')),
            temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.1')),
            use_trust3=os.getenv('USE_TRUST3', 'true').lower() == 'true',
            openai_base_url=os.getenv('OPENAI_BASE_URL')
        )
        try:
            return AIProcessor(config)
        except Exception as e:
            print(f"⚠️  OpenAI setup failed: {e}")
            # Do not fallback; caller should present a clear message
            return None