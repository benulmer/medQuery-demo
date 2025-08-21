from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from copy import deepcopy


class UserRole(Enum):
    DOCTOR = "doctor"
    RESEARCHER = "researcher"
    MARKETING = "marketing"
    INTERN = "intern"


@dataclass
class User:
    id: str
    name: str
    role: UserRole


@dataclass
class PatientData:
    id: str
    name: str
    age: int
    gender: str
    conditions: List[str]
    medications: List[str]
    notes: str
    address: str
    visit_dates: List[str]


class AccessControl:
    """Manages role-based access control for patient data"""
    
    def __init__(self, user_role: UserRole):
        self.user_role = user_role
        self._define_permissions()
    
    def _define_permissions(self):
        """Define what each role can access"""
        self.permissions = {
            UserRole.DOCTOR: {
                'can_view_identifying_info': True,
                'can_view_medical_details': True,
                'can_view_aggregated_stats': True,
                'redacted_fields': []
            },
            UserRole.RESEARCHER: {
                'can_view_identifying_info': False,
                'can_view_medical_details': True,
                'can_view_aggregated_stats': True,
                'redacted_fields': ['name', 'address']
            },
            UserRole.MARKETING: {
                'can_view_identifying_info': False,
                'can_view_medical_details': False,
                'can_view_aggregated_stats': True,
                'redacted_fields': ['name', 'address', 'notes', 'visit_dates']
            },
            UserRole.INTERN: {
                'can_view_identifying_info': False,
                'can_view_medical_details': False,
                'can_view_aggregated_stats': False,
                'redacted_fields': ['name', 'address', 'notes', 'visit_dates', 'conditions', 'medications']
            }
        }
    
    def filter_patient_data(self, patient: PatientData) -> Dict[str, Any]:
        """Filter patient data based on user permissions"""
        # Convert patient to dict for easier manipulation
        patient_dict = {
            'id': patient.id,
            'name': patient.name,
            'age': patient.age,
            'gender': patient.gender,
            'conditions': patient.conditions,
            'medications': patient.medications,
            'notes': patient.notes,
            'address': patient.address,
            'visit_dates': patient.visit_dates
        }
        
        # Apply redactions based on role
        redacted_fields = self.permissions[self.user_role]['redacted_fields']
        filtered_data = deepcopy(patient_dict)
        
        for field in redacted_fields:
            if field in filtered_data:
                if isinstance(filtered_data[field], list):
                    filtered_data[field] = []
                else:
                    filtered_data[field] = "[REDACTED]"
        
        return filtered_data
    
    def can_access_field(self, field_name: str) -> bool:
        """Check if the current user can access a specific field"""
        redacted_fields = self.permissions[self.user_role]['redacted_fields']
        return field_name not in redacted_fields
    
    def get_permissions_description(self) -> List[str]:
        """Get human-readable permissions for the current role"""
        perms = self.permissions[self.user_role]
        descriptions = []
        
        if perms['can_view_identifying_info']:
            descriptions.append("✅ Full access to all patient fields")
            descriptions.append("✅ Can view individual patient records")
            descriptions.append("✅ Can view identifying information")
        else:
            descriptions.append("❌ No access to identifying information")
            descriptions.append("✅ Can view de-identified records only" if perms['can_view_medical_details'] else "❌ No direct patient data access")
        
        if perms['can_view_aggregated_stats']:
            descriptions.append("✅ Can access aggregated statistics")
        else:
            descriptions.append("❌ Requires supervision for any queries")
        
        return descriptions
    
    def check_query_permission(self, query_type: str) -> bool:
        """Check if user has permission for a specific query type"""
        perms = self.permissions[self.user_role]
        
        if query_type == "help":
            return True
        if query_type == "individual_patient":
            return perms['can_view_medical_details']
        elif query_type == "aggregate_stats":
            return perms['can_view_aggregated_stats']
        elif query_type == "identifying_info":
            return perms['can_view_identifying_info']
        
        return False