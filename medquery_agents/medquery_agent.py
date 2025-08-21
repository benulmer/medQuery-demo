import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from medquery_utils.access_control import PatientData, User, UserRole, AccessControl
from medquery_utils.summarizer import PatientSummarizer, PopulationStats, SummaryOptions
from medquery_utils.fastmcp_client import FastMCPBridge
from medquery_utils.ai_processor import AIProcessor, QueryResult


@dataclass
class QueryContext:
    user: User
    patients: List[Dict[str, Any]]


class MedQueryAgent:
    """Main agent for processing medical queries with role-based access control"""
    
    def __init__(self, context: QueryContext):
        self.context = context
        self.summarizer = PatientSummarizer()
        self.population_stats = PopulationStats()
        self.ai_processor = None
        # FastMCP-only client (stdio or SSE based on env)
        import os
        self.fastmcp: FastMCPBridge | None = None
        try:
            self.fastmcp = FastMCPBridge.initialize_from_env()
            if self.fastmcp:
                print(f"🧩 FastMCP client enabled (mode={self.fastmcp.mode})")
        except Exception as e:
            print(f"⚠️  FastMCP unavailable: {e}")
        self.use_ai = False
        self._initialize_ai()
    
    def _initialize_ai(self):
        """Initialize AI processor if available"""
        self.ai_processor = AIProcessor.initialize_from_env()
        if self.ai_processor:
            self.use_ai = True
            model = self.ai_processor.config.model
            trust3_status = "with Trust3 Shield" if self.ai_processor.config.use_trust3 else "without Trust3"
            print(f"🤖 AI Mode: Ollama integration enabled ({model}) {trust3_status}")
        else:
            print("📋 Rule-Based Mode: Ollama not available")
    
    async def process_query(self, query: str) -> QueryResult:
        """Process a query using either AI or rule-based approach"""
        try:
            # Prefer deterministic/rule-based for known categories (enables MCP path)
            category = self._categorize_query(query)
            if category in ("aggregate_stats", "individual_patient", "help"):
                return await self._process_query_rule_based(query)

            # Fall back to AI for general queries
            if self.use_ai and self.ai_processor:
                try:
                    return await self.ai_processor.process_query(query, self.context.user, self.context.patients)
                except Exception:
                    # If AI fails, try rule-based as a safe fallback
                    return await self._process_query_rule_based(query)
            return await self._process_query_rule_based(query)
        except Exception as e:
            return QueryResult(
                success=False,
                message=f"Error processing query: {str(e)}",
                access_level=self.context.user.role,
                redacted_fields=[]
            )
    
    async def _process_query_rule_based(self, query: str) -> QueryResult:
        """Process query using rule-based categorization"""
        access_control = AccessControl(self.context.user.role)
        
        # Categorize the query
        query_type = self._categorize_query(query)
        
        # Check permissions for this query type
        if not access_control.check_query_permission(query_type):
            if self.context.user.role == UserRole.INTERN:
                return QueryResult(
                    success=True,
                    message="Access to patient data requires supervision. Please contact your supervisor for assistance.",
                    access_level=self.context.user.role,
                    redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
                )
            else:
                return QueryResult(
                    success=True,
                    message="Access denied. You don't have permission for this type of query.",
                    access_level=self.context.user.role,
                    redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
                )
        
        # Process based on query type
        if query_type == "help":
            return await self._handle_help_query(access_control)
        if query_type == "individual_patient":
            return await self._handle_individual_patient_query(query, access_control)
        elif query_type == "aggregate_stats":
            return await self._handle_aggregate_query(query, access_control)
        else:
            return await self._handle_general_query(query, access_control)
    
    def _categorize_query(self, query: str) -> str:
        """Categorize the query to determine processing approach"""
        query_lower = query.lower()
        
        # Help / usage queries
        help_patterns = [
            r"example.*id",
            r"id.*format",
            r"valid.*id",
            r"how.*reference.*patient",
            r"how.*use.*id",
            r"what.*is.*patient.*id",
            r"how.*find.*patient.*id",
        ]
        if any(re.search(pattern, query_lower) for pattern in help_patterns):
            return "help"

        # Individual patient queries
        individual_patterns = [
            r"summarize.*patient",
            r"patient.*history",
            r"medication.*history.*patient",
            r"patient.*id.*\d+",
            r"(jane|john|david|maria|smith|chen|lopez).*health",
            r"patient.*named"
        ]
        
        if any(re.search(pattern, query_lower) for pattern in individual_patterns):
            return "individual_patient"
        
        # Aggregate statistics queries
        aggregate_patterns = [
            r"how many.*patients",
            r"percentage.*patients",
            r"average.*age",
            r"patients.*with.*diabetes",
            r"find.*patients.*aged",
            r"statistics.*about",
            r"all patients.*taking"
        ]
        
        if any(re.search(pattern, query_lower) for pattern in aggregate_patterns):
            return "aggregate_stats"
        
        # Default to general query
        return "general"

    async def _handle_help_query(self, access_control: AccessControl) -> QueryResult:
        """Provide quick usage help and sample IDs locally."""
        sample_ids = [p.get('id') for p in (self.context.patients or [])][:5]
        tips = [
            "Use patient IDs like P0001, P0062, P0123",
            "Examples:",
            "- Summarize patient ID P0001",
            "- What is the medication history of patient ID P0062?",
            "- Find patients aged 60 with Type 2 Diabetes",
        ]
        if sample_ids:
            tips.insert(1, f"Here are a few IDs you can use: {', '.join(sample_ids)}")
        return QueryResult(
            success=True,
            message="\n".join(tips),
            access_level=self.context.user.role,
            redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
        )
    
    async def _handle_individual_patient_query(self, query: str, access_control: AccessControl) -> QueryResult:
        """Handle queries about individual patients"""
        query_lower = query.lower()
        
        # Try to find specific patient by name or ID
        target_patient = None
        
        # Check for patient ID
        id_match = re.search(r"patient.*id.*(\w+)", query_lower)
        if id_match:
            patient_id = id_match.group(1).upper()
            target_patient = next((p for p in self.context.patients if p['id'].upper() == patient_id), None)
        
        # Check for patient names
        if not target_patient:
            name_patterns = {
                r"jane.*smith": "P001",
                r"david.*chen": "P002", 
                r"maria.*lopez": "P003"
            }
            
            for pattern, patient_id in name_patterns.items():
                if re.search(pattern, query_lower):
                    target_patient = next((p for p in self.context.patients if p['id'] == patient_id), None)
                    break
        
        if not target_patient and self.fastmcp:
            # Try FastMCP lookup by parsed id or name
            pid = None
            name = None
            m = re.search(r"\b(p\d{3,5})\b", query_lower)
            if m:
                pid = m.group(1).upper()
            nm = re.search(r"patient named ([a-z ]+)", query_lower)
            if nm:
                name = nm.group(1).title()
            try:
                p = await self.fastmcp.call_tool('patient_get', {'id': pid, 'name': name})
                if p:
                    target_patient = p
            except Exception:
                pass
        if not target_patient:
            return QueryResult(
                success=True,
                message="Patient not found. Please specify a valid patient name or ID.",
                access_level=self.context.user.role,
                redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
            )
        
        # Filter patient data based on permissions
        filtered_patient = access_control.filter_patient_data(PatientData(**target_patient))
        
        # Generate summary
        summary = self.summarizer.summarize_patient(filtered_patient)
        
        return QueryResult(
            success=True,
            message=summary,
            access_level=self.context.user.role,
            redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
        )
    
    async def _handle_aggregate_query(self, query: str, access_control: AccessControl) -> QueryResult:
        """Handle aggregate statistical queries"""
        query_lower = query.lower()
        
        # Prefer FastMCP for cohorts/aggregates if available
        if self.fastmcp:
            min_age = None
            conditions = []
            m = re.search(r"aged?\s*(\d+)", query_lower)
            if m:
                try:
                    min_age = int(m.group(1))
                except Exception:
                    min_age = None
            for c in ["type 2 diabetes", "asthma", "hypertension", "high cholesterol"]:
                if c in query_lower:
                    conditions.append(c.title())
            try:
                if "aggregate" in query_lower or "count" in query_lower or "percentage" in query_lower:
                    aggs = await self.fastmcp.call_tool(
                        "patient_aggregate",
                        {"min_age": min_age, "conditions": conditions or None},
                    )
                    lines = [f"{a['medication']}: {a['count']}" for a in aggs]
                    text = "Medication counts" + (f" (age≥{min_age})" if min_age else "")
                    if conditions:
                        text += f" for {', '.join(conditions)}"
                    text += ":\n" + "\n".join(lines or ["No matches"])
                    return QueryResult(success=True, message=text, access_level=self.context.user.role, redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields'])
                # cohort listing
                results = await self.fastmcp.call_tool(
                    "patient_search",
                    {"min_age": min_age, "conditions": conditions or None, "limit": 25},
                )
                lines = [f"- {r.get('id')}: {r.get('name')} {r.get('age')}{r.get('gender','')} | {', '.join(r.get('conditions') or [])}" for r in results]
                text = "Cohort sample (first 25)" + (f" age≥{min_age}" if min_age else "")
                if conditions:
                    text += f" with {', '.join(conditions)}"
                text += ":\n" + "\n".join(lines or ["No matches"])
                return QueryResult(success=True, message=text, access_level=self.context.user.role, redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields'])
            except Exception:
                pass
        # No HTTP MCP fallback; continue to in-memory processing
        
        # Fallback to in-memory processing
        filtered_patients = [
            access_control.filter_patient_data(PatientData(**patient))
            for patient in self.context.patients
        ]

        # Detect query type and parameters
        if "percentage" in query_lower and "metformin" in query_lower:
            age_filter = None
            if "under 40" in query_lower or "< 40" in query_lower:
                age_filter = {"max_age": 39}
            elif "over 40" in query_lower or "> 40" in query_lower:
                age_filter = {"min_age": 41}
            
            result = self.population_stats.get_percentage_with_medication(
                filtered_patients, "Metformin", age_filter
            )
            
            if "error" in result:
                return QueryResult(
                    success=False,
                    message=result["error"],
                    access_level=self.context.user.role,
                    redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
                )
            
            message = f"Metformin Usage Analysis:\n"
            message += f"• Total patients in group: {result['total_patients_in_group']}\n"
            message += f"• Patients taking Metformin: {result['patients_with_medication']}\n"
            message += f"• Percentage: {result['percentage']}%"
            if result['age_filter'] != "None":
                message += f"\n• Age filter applied: {result['age_filter']}"
            
            return QueryResult(
                success=True,
                message=message,
                access_level=self.context.user.role,
                redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
            )
        
        elif "patients" in query_lower and "diabetes" in query_lower:
            criteria = {"condition": "Type 2 Diabetes"}
            
            # Check for age criteria
            if "aged 60+" in query_lower or "over 60" in query_lower:
                criteria["min_age"] = 60
            
            matching_patients = self.population_stats.get_patients_by_criteria(filtered_patients, **criteria)
            
            if not matching_patients:
                return QueryResult(
                    success=True,
                    message="No patients found matching the specified criteria.",
                    access_level=self.context.user.role,
                    redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
                )
            
            message = f"Found {len(matching_patients)} patients with Type 2 Diabetes"
            if "min_age" in criteria:
                message += f" aged {criteria['min_age']}+"
            message += ":\n\n"
            
            for patient in matching_patients:
                if patient.get('name') != "[REDACTED]":
                    message += f"• {patient['name']} (ID: {patient['id']}, Age: {patient['age']})\n"
                else:
                    message += f"• Patient ID: {patient['id']} (Age: {patient['age']})\n"
            
            return QueryResult(
                success=True,
                message=message,
                access_level=self.context.user.role,
                redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
            )
        
        elif "average age" in query_lower:
            stats = self.population_stats.get_aggregate_statistics(filtered_patients, "age")
            
            if "error" in stats:
                return QueryResult(
                    success=False,
                    message=stats["error"],
                    access_level=self.context.user.role,
                    redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
                )
            
            message = f"Age Statistics:\n"
            message += f"• Average age: {stats['average']} years\n"
            message += f"• Age range: {stats['min']} - {stats['max']} years\n"
            message += f"• Total patients: {stats['count']}"
            
            return QueryResult(
                success=True,
                message=message,
                access_level=self.context.user.role,
                redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
            )
        
        else:
            return QueryResult(
                success=True,
                message="I can help with specific aggregate queries like:\n• 'What percentage of patients under 40 are on Metformin?'\n• 'Find all patients aged 60+ with Type 2 Diabetes'\n• 'What's the average age of patients?'",
                access_level=self.context.user.role,
                redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
            )
    
    async def _handle_general_query(self, query: str, access_control: AccessControl) -> QueryResult:
        """Handle general system queries"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["help", "what can", "how does", "example"]):
            # Generate role-specific examples
            examples = self._get_example_queries(self.context.user.role)
            message = "I can help you with medical queries. Here are some examples of what you can ask:\n\n"
            message += "\n".join(f"• {example}" for example in examples)
            
            return QueryResult(
                success=True,
                message=message,
                access_level=self.context.user.role,
                redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
            )
        
        else:
            # Default response with examples
            examples = self._get_example_queries(self.context.user.role)
            message = "I can help you with medical queries. Here are some examples of what you can ask:\n\n"
            message += "\n".join(f"• '{example}'" for example in examples)
            
            return QueryResult(
                success=True,
                message=message,
                access_level=self.context.user.role,
                redacted_fields=access_control.permissions[self.context.user.role]['redacted_fields']
            )
    
    def _get_example_queries(self, role: UserRole) -> List[str]:
        """Get role-specific example queries"""
        examples = {
            UserRole.DOCTOR: [
                "Summarize Jane Smith's health history",
                "What is the medication history of patient ID P001?",
                "Find patients with Type 2 Diabetes",
                "Show me all patients taking Metformin"
            ],
            UserRole.RESEARCHER: [
                "Find all patients aged 60+ with Type 2 Diabetes",
                "What's the average age of patients with Hypertension?",
                "Show demographics of patients taking Lisinopril",
                "How many patients have Asthma?"
            ],
            UserRole.MARKETING: [
                "What percentage of patients under 40 are on Metformin?",
                "What's the average age of patients with mild hypertension?",
                "Show patient age distribution",
                "How many patients are in each age group?"
            ],
            UserRole.INTERN: [
                "What can I do with this system?",
                "How does access control work?",
                "What are the different user roles?",
                "Access to patient data requires supervision"
            ]
        }
        
        return examples.get(role, ["General system information available"])