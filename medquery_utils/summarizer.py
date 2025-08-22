from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import Counter
from medquery_utils.access_control import PatientData, AccessControl, UserRole


@dataclass
class SummaryOptions:
    include_demographics: bool = True
    include_conditions: bool = True
    include_medications: bool = True
    include_notes: bool = True
    include_visits: bool = True


class PatientSummarizer:
    """Generates patient summaries with access control"""
    
    def summarize_patient(self, patient_data: Dict[str, Any], options: SummaryOptions = None) -> str:
        """Generate a formatted summary of a patient's data"""
        if options is None:
            options = SummaryOptions()
        
        summary_parts = []
        
        # Patient identification
        if patient_data.get('name') and patient_data['name'] != "[REDACTED]":
            summary_parts.append(f"Patient: {patient_data['name']}")
        else:
            summary_parts.append(f"Patient ID: {patient_data['id']}")
        
        # Demographics
        if options.include_demographics:
            age = patient_data.get('age', 'Unknown')
            gender = patient_data.get('gender', 'Unknown')
            summary_parts.append(f"Demographics: {age} years old, {gender}")
        
        # Medical conditions
        if options.include_conditions and patient_data.get('conditions'):
            conditions = patient_data['conditions']
            if conditions and conditions != []:
                summary_parts.append(f"Conditions: {', '.join(conditions)}")
        
        # Current medications
        if options.include_medications and patient_data.get('medications'):
            medications = patient_data['medications']
            if medications and medications != []:
                summary_parts.append(f"Current Medications: {', '.join(medications)}")
        
        # Clinical notes
        if options.include_notes and patient_data.get('notes'):
            notes = patient_data['notes']
            if notes and notes != "[REDACTED]":
                summary_parts.append(f"Clinical Notes: {notes}")
        
        # Visit history
        if options.include_visits and patient_data.get('visit_dates'):
            visits = patient_data['visit_dates']
            if visits and visits != []:
                visit_count = len(visits)
                most_recent = max(visits) if visits else "Unknown"
                summary_parts.append(f"Visit History: {visit_count} visits, most recent on {most_recent}")
        
        # Address (if available)
        if patient_data.get('address') and patient_data['address'] != "[REDACTED]":
            summary_parts.append(f"Address: {patient_data['address']}")
        
        return "\n".join(summary_parts)


class PopulationStats:
    """Generates population-level statistics"""
    
    def get_patients_by_criteria(self, patients: List[Dict[str, Any]], **criteria) -> List[Dict[str, Any]]:
        """Find patients matching specific criteria"""
        matching_patients = []
        
        for patient in patients:
            matches = True
            
            # Check age criteria
            if 'min_age' in criteria:
                if patient.get('age', 0) < criteria['min_age']:
                    matches = False
            
            if 'max_age' in criteria:
                if patient.get('age', 999) > criteria['max_age']:
                    matches = False
            
            # Check condition criteria
            if 'condition' in criteria:
                patient_conditions = patient.get('conditions', [])
                if criteria['condition'] not in patient_conditions:
                    matches = False
            
            # Check medication criteria
            if 'medication' in criteria:
                patient_medications = patient.get('medications', [])
                if criteria['medication'] not in patient_medications:
                    matches = False
            
            # Check gender criteria
            if 'gender' in criteria:
                if patient.get('gender', '').lower() != criteria['gender'].lower():
                    matches = False
            
            if matches:
                matching_patients.append(patient)
        
        return matching_patients
    
    def get_aggregate_statistics(self, patients: List[Dict[str, Any]], field: str) -> Dict[str, Any]:
        """Generate aggregate statistics for a specific field"""
        if not patients:
            return {"error": "No patients provided"}
        
        if field == 'age':
            ages = [p.get('age', 0) for p in patients if p.get('age')]
            if not ages:
                return {"error": "No age data available"}
            
            return {
                "count": len(ages),
                "average": round(sum(ages) / len(ages), 1),
                "min": min(ages),
                "max": max(ages),
                "median": sorted(ages)[len(ages) // 2]
            }
        
        elif field == 'gender':
            genders = [p.get('gender', 'Unknown') for p in patients]
            gender_counts = Counter(genders)
            total = len(genders)
            
            return {
                "total_patients": total,
                "distribution": {
                    gender: {
                        "count": count,
                        "percentage": round((count / total) * 100, 1)
                    }
                    for gender, count in gender_counts.items()
                }
            }
        
        elif field == 'conditions':
            all_conditions = []
            for patient in patients:
                conditions = patient.get('conditions', [])
                all_conditions.extend(conditions)
            
            if not all_conditions:
                return {"error": "No condition data available"}
            
            condition_counts = Counter(all_conditions)
            total_patients = len(patients)
            
            return {
                "total_patients": total_patients,
                "unique_conditions": len(condition_counts),
                "most_common": [
                    {
                        "condition": condition,
                        "patient_count": count,
                        "percentage": round((count / total_patients) * 100, 1)
                    }
                    for condition, count in condition_counts.most_common(5)
                ]
            }
        
        elif field == 'medications':
            all_medications = []
            for patient in patients:
                medications = patient.get('medications', [])
                all_medications.extend(medications)
            
            if not all_medications:
                return {"error": "No medication data available"}
            
            medication_counts = Counter(all_medications)
            total_patients = len(patients)
            
            return {
                "total_patients": total_patients,
                "unique_medications": len(medication_counts),
                "most_common": [
                    {
                        "medication": medication,
                        "patient_count": count,
                        "percentage": round((count / total_patients) * 100, 1)
                    }
                    for medication, count in medication_counts.most_common(5)
                ]
            }
        
        else:
            return {"error": f"Statistics not available for field: {field}"}
    
    def get_percentage_with_medication(self, patients: List[Dict[str, Any]], medication: str, age_filter: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Get percentage of patients on a specific medication, optionally filtered by age"""
        filtered_patients = patients
        
        # Apply age filter if provided
        if age_filter:
            if 'min_age' in age_filter or 'max_age' in age_filter:
                filtered_patients = self.get_patients_by_criteria(
                    patients, 
                    **age_filter
                )
        
        if not filtered_patients:
            return {"error": "No patients match the criteria"}
        
        total_patients = len(filtered_patients)
        patients_with_medication = len(self.get_patients_by_criteria(
            filtered_patients, 
            medication=medication
        ))
        
        percentage = round((patients_with_medication / total_patients) * 100, 1)
        
        return {
            "total_patients_in_group": total_patients,
            "patients_with_medication": patients_with_medication,
            "percentage": percentage,
            "medication": medication,
            "age_filter": age_filter or "None"
        }