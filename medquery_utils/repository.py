from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    ForeignKey,
    create_engine,
    Index,
    select,
    func,
)
from sqlalchemy.orm import declarative_base, relationship, Session, Mapped, mapped_column


Base = declarative_base()


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[Optional[str]] = mapped_column(String(8))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    visits: Mapped[List[Visit]] = relationship("Visit", back_populates="patient", cascade="all, delete-orphan")
    conditions: Mapped[List[PatientCondition]] = relationship("PatientCondition", back_populates="patient", cascade="all, delete-orphan")
    medications: Mapped[List[PatientMedication]] = relationship("PatientMedication", back_populates="patient", cascade="all, delete-orphan")


class Condition(Base):
    __tablename__ = "conditions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)


class Medication(Base):
    __tablename__ = "medications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)


class PatientCondition(Base):
    __tablename__ = "patient_conditions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    condition_id: Mapped[int] = mapped_column(ForeignKey("conditions.id", ondelete="CASCADE"))

    patient: Mapped[Patient] = relationship("Patient", back_populates="conditions")
    condition: Mapped[Condition] = relationship("Condition")


class PatientMedication(Base):
    __tablename__ = "patient_medications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    medication_id: Mapped[int] = mapped_column(ForeignKey("medications.id", ondelete="CASCADE"))

    patient: Mapped[Patient] = relationship("Patient", back_populates="medications")
    medication: Mapped[Medication] = relationship("Medication")


class Visit(Base):
    __tablename__ = "visits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    visit_date: Mapped[str] = mapped_column(String(10))  # ISO date

    patient: Mapped[Patient] = relationship("Patient", back_populates="visits")


Index("ix_patient_age", Patient.age)
Index("ix_visit_patient_date", Visit.patient_id, Visit.visit_date)


@dataclass
class PatientFilter:
    min_age: Optional[int] = None
    condition_names: Optional[List[str]] = None


class PatientRepository:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url, future=True)
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return Session(self.engine, future=True)

    def upsert_from_json(self, patients: List[Dict[str, Any]]) -> int:
        with self.session() as s, s.begin():
            # Preload dictionaries
            name_to_condition: Dict[str, Condition] = {c.name: c for c in s.scalars(select(Condition)).all()}
            name_to_med: Dict[str, Medication] = {m.name: m for m in s.scalars(select(Medication)).all()}

            count = 0
            for p in patients:
                ext_id = p.get("id") or f"P{count+1:04d}"
                patient = s.scalar(select(Patient).where(Patient.external_id == ext_id))
                if not patient:
                    patient = Patient(external_id=ext_id)
                    s.add(patient)

                patient.name = p.get("name")
                patient.age = int(p.get("age") or 0)
                patient.gender = p.get("gender")
                patient.address = p.get("address")
                patient.notes = p.get("notes")

                # Clear existing relations
                patient.conditions.clear()
                patient.medications.clear()
                patient.visits.clear()

                for cname in p.get("conditions", []) or []:
                    c = name_to_condition.get(cname)
                    if not c:
                        c = Condition(name=cname)
                        s.add(c)
                        s.flush()
                        name_to_condition[cname] = c
                    patient.conditions.append(PatientCondition(condition=c))

                for mname in p.get("medications", []) or []:
                    m = name_to_med.get(mname)
                    if not m:
                        m = Medication(name=mname)
                        s.add(m)
                        s.flush()
                        name_to_med[mname] = m
                    patient.medications.append(PatientMedication(medication=m))

                for v in p.get("visit_dates", []) or []:
                    patient.visits.append(Visit(visit_date=str(v)))

                count += 1
            return count

    def count_patients(self) -> int:
        with self.session() as s:
            return int(s.scalar(select(func.count(Patient.id))) or 0)

    def search_patients(self, pf: PatientFilter, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with self.session() as s:
            stmt = select(Patient).limit(limit).offset(offset)
            if pf.min_age is not None:
                stmt = stmt.where(Patient.age >= pf.min_age)

            if pf.condition_names:
                stmt = (
                    stmt.join(Patient.conditions)
                    .join(PatientCondition.condition)
                    .where(Condition.name.in_(pf.condition_names))
                )

            rows = s.scalars(stmt).unique().all()
            result: List[Dict[str, Any]] = []
            for p in rows:
                result.append({
                    "id": p.external_id,
                    "name": p.name,
                    "age": p.age,
                    "gender": p.gender,
                    "address": p.address,
                    "notes": p.notes,
                    "conditions": [pc.condition.name for pc in p.conditions],
                    "medications": [pm.medication.name for pm in p.medications],
                    "visit_dates": [v.visit_date for v in p.visits],
                })
            return result

    def aggregate_by_medication(self, pf: PatientFilter) -> List[Tuple[str, int]]:
        with self.session() as s:
            stmt = (
                select(Medication.name, func.count(PatientMedication.id))
                .join(PatientMedication, PatientMedication.medication_id == Medication.id)
                .join(Patient, Patient.id == PatientMedication.patient_id)
                .group_by(Medication.name)
                .order_by(func.count(PatientMedication.id).desc())
            )
            if pf.min_age is not None:
                stmt = stmt.where(Patient.age >= pf.min_age)
            if pf.condition_names:
                stmt = (
                    stmt.join(PatientCondition, PatientCondition.patient_id == Patient.id)
                    .join(Condition, Condition.id == PatientCondition.condition_id)
                    .where(Condition.name.in_(pf.condition_names))
                )
            return [(name, int(count)) for name, count in s.execute(stmt).all()]

