#!/usr/bin/env python3
"""
MedQuery AI Web Interface
A beautiful ChatGPT-style web interface for healthcare data queries
"""

import os
import sys
import asyncio
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import uuid
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

from medquery_utils.access_control import User, UserRole, PatientData, AccessControl
from medquery_utils.summarizer import PatientSummarizer, PopulationStats
from medquery_agents.medquery_agent import MedQueryAgent, QueryContext
from medquery_utils.ai_processor import QueryResult
from medquery_utils.repository import PatientRepository, PatientFilter

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Global agent instance
medquery_agent = None
patient_data = []
patient_repo: PatientRepository = None

def load_patient_data():
    """Load patient data from JSON file"""
    global patient_data
    import json
    
    data_file = os.path.join(os.getcwd(), 'Data', 'mock_patient_data.json')
    try:
        with open(data_file, 'r') as f:
            patient_data = json.load(f)
        print(f"✅ Loaded {len(patient_data)} patient records")
        return True
    except Exception as e:
        print(f"❌ Error loading patient data: {e}")
        return False

def initialize_agent():
    """Initialize the MedQuery agent (will be created per session)"""
    global medquery_agent, patient_repo
    # Initialize repository (SQLite by default)
    db_url = os.getenv('DATABASE_URL', 'sqlite:///./medquery.db')
    patient_repo = PatientRepository(db_url)
    # Seed from JSON at startup for demo
    if load_patient_data():
        try:
            imported = patient_repo.upsert_from_json(patient_data)
            print(f"📥 Seeded {imported} patients into DB")
        except Exception as e:
            print(f"⚠️  Seeding DB failed: {e}")
        medquery_agent = True  # Just mark as ready
        return True
    return False

@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

@app.route('/api/users')
def get_users():
    """Get available users for role selection"""
    users = [
        {"id": "sarah_johnson", "name": "Dr. Sarah Johnson", "role": "doctor", "avatar": "👩‍⚕️"},
        {"id": "michael_chen", "name": "Dr. Michael Chen", "role": "researcher", "avatar": "👨‍🔬"},
        {"id": "alice_thompson", "name": "Alice Thompson", "role": "marketing", "avatar": "👩‍💼"},
        {"id": "david_wilson", "name": "David Wilson", "role": "intern", "avatar": "👨‍🎓"}
    ]
    return jsonify({"users": users})

@app.route('/api/user/select', methods=['POST'])
def select_user():
    """Select a user and set up session"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    # Map user IDs to user objects
    user_map = {
        "sarah_johnson": User("sarah_johnson", "Dr. Sarah Johnson", UserRole.DOCTOR),
        "michael_chen": User("michael_chen", "Dr. Michael Chen", UserRole.RESEARCHER),
        "alice_thompson": User("alice_thompson", "Alice Thompson", UserRole.MARKETING),
        "david_wilson": User("david_wilson", "David Wilson", UserRole.INTERN)
    }
    
    if user_id in user_map:
        user = user_map[user_id]
        session['current_user'] = {
            'id': user_id,
            'name': user.name,
            'role': user.role.value
        }
        
        # Agent will be created per request with proper context
        
        # Get permissions for this role
        access_control = AccessControl(user.role)
        permissions = access_control.get_permissions_description()
        
        return jsonify({
            "success": True,
            "user": session['current_user'],
            "permissions": permissions
        })
    
    return jsonify({"success": False, "error": "Invalid user ID"}), 400

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process a chat message"""
    if not session.get('current_user'):
        return jsonify({"error": "No user selected"}), 401
    
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"error": "Empty message"}), 400
    
    try:
        # Create user object from session
        user_data = session['current_user']
        user = User(user_data['id'], user_data['name'], UserRole(user_data['role']))
        
        # Create agent context and agent for this request
        context = QueryContext(user=user, patients=patient_data)
        agent = MedQueryAgent(context)
        
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(agent.process_query(message))
        finally:
            loop.close()
        
        # Format response
        response = {
            "message": result.message,
            "success": result.success,
            "access_level": result.access_level.value,
            "redacted_fields": result.redacted_fields or [],
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Error processing chat: {e}")
        return jsonify({
            "message": f"Sorry, I encountered an error: {str(e)}",
            "success": False,
            "access_level": session['current_user']['role'],
            "redacted_fields": [],
            "timestamp": datetime.now().isoformat()
        })

@app.route('/api/health')
def health():
    """Health check endpoint"""
    db_count = None
    try:
        if patient_repo:
            db_count = patient_repo.count_patients()
    except Exception:
        db_count = None
    return jsonify({
        "status": "healthy",
        "agent_ready": medquery_agent is not None,
        "patient_records": len(patient_data),
        "db_records": db_count,
        "trust3_enabled": hasattr(medquery_agent, 'ai_processor') and 
                         medquery_agent.ai_processor is not None if medquery_agent else False
    })

if __name__ == '__main__':
    print("🏥 Starting MedQuery AI Web Interface...")
    
    if initialize_agent():
        print("🚀 MedQuery AI is ready!")
        # Disable debug reloader to preserve environment variables and avoid double-spawn
        app.run(debug=False, use_reloader=False, host='0.0.0.0', port=5000)
    else:
        print("❌ Failed to initialize MedQuery AI")
        sys.exit(1)