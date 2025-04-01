from pymongo import MongoClient
from typing import List, Dict, Any, Optional
import datetime
import os

# MongoDB connection parameters
# In production, use environment variables or a secure configuration system
MONGO_URI = "mongodb+srv://RasaAgent1:RasaAgent1@rasaagent.kwrksnw.mongodb.net/?retryWrites=true&w=majority&appName=RasaAgent"
DB_NAME = "RasaAgent"

def get_db_connection():
    """Establish and return a connection to the MongoDB database."""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        # Test the connection
        client.admin.command('ping')
        print("Database connection successful")
        return db
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def find_clinics(location: str, clinic_type: str = "general") -> List[Dict[str, Any]]:
    """
    Find clinics based on location and type.
    
    Args:
        location: The user's location
        clinic_type: The type of clinic services needed
        
    Returns:
        A list of clinic dictionaries with details
    """
    db = get_db_connection()
    if db is None:  # Changed from "if not db:" to "if db is None:"
        print("Failed to connect to database")
        return []
    
    try:
        # Create a case-insensitive regex pattern for location
        location_pattern = {"$regex": location, "$options": "i"}
        
        # Query for clinics matching the location and type
        query = {
            "location": location_pattern,
            "$or": [
                {"type": clinic_type},
                {"type": "general"}
            ]
        }
        
        # If clinic_type is "general", we don't need the $or condition
        if clinic_type == "general":
            query = {"location": location_pattern}
        
        print(f"Executing MongoDB query: {query}")
        
        # Find clinics and sort by distance
        clinics = list(db.clinics.find(query).sort("distance_miles", 1))
        
        print(f"Found {len(clinics)} clinics matching the query")
        
        # Convert ObjectId to string for JSON serialization
        for clinic in clinics:
            clinic["id"] = str(clinic["_id"])
            del clinic["_id"]
        
        return clinics
    except Exception as e:
        print(f"Database query error in find_clinics: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_available_slots(clinic_id: str, date_str: str) -> List[Dict[str, Any]]:
    """
    Get available appointment slots for a specific clinic and date.
    
    Args:
        clinic_id: The ID of the selected clinic
        date_str: The date for appointment in YYYY-MM-DD format
        
    Returns:
        A list of available time slots
    """
    db = get_db_connection()
    if db is None:  # Changed from "if not db:" to "if db is None:"
        print("Failed to connect to database")
        return []
    
    try:
        # Parse the date string
        appointment_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Query for available slots
        query = {
            "clinic_id": clinic_id,
            "appointment_date": appointment_date.isoformat(),
            "is_available": True
        }
        
        print(f"Executing slots query: {query}")
        
        # Find slots and sort by time
        slots = list(db.appointment_slots.find(query).sort("time_slot", 1))
        
        print(f"Found {len(slots)} available slots")
        
        # Convert ObjectId to string for JSON serialization
        for slot in slots:
            slot["id"] = str(slot["_id"])
            del slot["_id"]
        
        return slots
    except Exception as e:
        print(f"Database query error in get_available_slots: {e}")
        import traceback
        traceback.print_exc()
        return []

def book_appointment(slot_id: str, user_info: str) -> bool:
    """
    Book an appointment by marking a slot as unavailable.
    
    Args:
        slot_id: The ID of the selected time slot
        user_info: User contact information
        
    Returns:
        Boolean indicating success or failure
    """
    from bson.objectid import ObjectId
    
    db = get_db_connection()
    if db is None:
        print("Failed to connect to database")
        return False
    
    try:
        # First, check if the slot is still available
        slot = db.appointment_slots.find_one({"_id": ObjectId(slot_id)})
        if not slot or not slot.get("is_available", False):
            print(f"Slot {slot_id} is no longer available")
            return False
            
        # Update the slot to mark it as booked
        result = db.appointment_slots.update_one(
            {"_id": ObjectId(slot_id), "is_available": True},
            {"$set": {"is_available": False, "booked_by": user_info, "booking_time": datetime.datetime.now()}}
        )
        
        # Check if the update was successful
        success = result.modified_count > 0
        if success:
            print(f"Successfully booked slot {slot_id} for {user_info}")
        else:
            print(f"Failed to book slot {slot_id}, no documents were modified")
        
        return success
    except Exception as e:
        print(f"Database update error in book_appointment: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_clinic_details(clinic_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific clinic.
    
    Args:
        clinic_id: The ID of the clinic
        
    Returns:
        A dictionary with clinic details or None if not found
    """
    from bson.objectid import ObjectId
    
    db = get_db_connection()
    if db is None:  # Changed from "if not db:" to "if db is None:"
        print("Failed to connect to database")
        return None
    
    try:
        # Query for the clinic by ID
        clinic = db.clinics.find_one({"_id": ObjectId(clinic_id)})
        
        if clinic:
            # Convert ObjectId to string for JSON serialization
            clinic["id"] = str(clinic["_id"])
            del clinic["_id"]
            return clinic
        
        return None
    except Exception as e:
        print(f"Database query error in get_clinic_details: {e}")
        import traceback
        traceback.print_exc()
        return None