import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from actions.db_utils import find_clinics, get_available_slots, book_appointment, get_clinic_details
import datetime

class ActionFindClinics(Action):
    def name(self) -> Text:
        return "action_ask_clinic_selection"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        location = tracker.get_slot("user_location") or "your area"
        appointment_topic = tracker.get_slot("appointment_topic")
        
        if not appointment_topic:
            dispatcher.utter_message(
                text="🤔 I need to know what type of appointment you're looking for. Could you please specify the healthcare service you need?"
            )
            return []
        
        # Fetch clinics from the MongoDB database
        clinics = find_clinics(location, appointment_topic)
        
        if clinics:
            message = f"🎉 I found {len(clinics)} clinics near {location} offering {appointment_topic} services!\n\n"
            
            # # Add clinic information to the message
            # for i, clinic in enumerate(clinics, 1):
            #     message += f"{i}. {clinic['name']} ({clinic['distance_miles']} miles away) - {clinic['phone']}\n"
            
            message += "\nWhich one would you like to check out? 😊"
            
            # Create buttons for clinic selection
            buttons = []
            for i, clinic in enumerate(clinics, 1):
                title = f"{i}. {clinic['name']} - {clinic['phone']}\n"
                payload = f"\"{i}\""
                buttons.append({"title": title, "payload": payload})
            
            dispatcher.utter_message(text=message, buttons=buttons)
        else:
            dispatcher.utter_message(
                text=f"😔 I couldn't find any clinics near {location} offering {appointment_topic} services. Would you like to try a different location or service type? I'm here to help! 💪"
            )
        
        # Store the clinics in a slot for later reference
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d")
        return [
            SlotSet("available_clinics", clinics),
            SlotSet("current_date_time", current_datetime)
        ]


class ActionConfirmAppointment(Action):
    def name(self) -> Text:
        return "action_ask_booking_confirmation"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        clinic_id = tracker.get_slot("selected_clinic_id")
        slot_id = tracker.get_slot("selected_slot_id")
        user_name = tracker.get_slot("user_name") or "there"
        user_info = tracker.get_slot("user_contact_info") or "your contact information"
        
        if not clinic_id or not slot_id:
            dispatcher.utter_message(
                text="🤔 I'm missing some information to book your appointment. Let's start by selecting a clinic and an appointment time. I'm here to guide you through the process! 👍"
            )
            return []
        
        # Get clinic details
        clinic = get_clinic_details(clinic_id)
        clinic_name = clinic['name'] if clinic else "the clinic"
        
        # Get slot details from the available_slots slot
        available_slots = tracker.get_slot("available_slots") or []
        slot_time = next((slot['time_slot'] for slot in available_slots if slot['id'] == slot_id), "the selected time")
        appointment_date = tracker.get_slot("booking_date") or "the selected date"
        
        # Prepare the booking details for confirmation
        booking_details = {
            "user_name": user_name,
            "clinic_name": clinic_name,
            "appointment_date": appointment_date,
            "slot_time": slot_time,
            "contact_info": user_info
        }
        
        message = (f"🎉 Here's your appointment summary:\n\n"
                    f"Name: {user_name}"
                    f"Clinic: {clinic_name}"
                    f"Date: {appointment_date}"
                    f"Time: {slot_time}"
                    f"Contact: {user_info}\n"
                    f"Please confirm if these details are correct.")
        buttons = [
            {"title": "Yes, they are correct. Proceed", "payload": "Yes, they are correct. Proceed"},
            {"title": "No, its wrong", "payload": "No, its wrong"}
        ]
        dispatcher.utter_message(text=message)
        
        # Store booking details for later use
        return [SlotSet("booking_details", booking_details)]


class ActionFindPregnancyClinics(Action):
    def name(self) -> Text:
        return "action_find_pregnancy_clinics"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        location = tracker.get_slot("user_location") or "your area"
        
        # Fetch pregnancy clinics from the database
        clinics = find_clinics(location, "pregnancy")
        
        if clinics:
            message = f"🌟 I found {len(clinics)} clinics near {location} offering pregnancy services:\n\n"
            
            # for i, clinic in enumerate(clinics, 1):
            #     message += f"{i}. {clinic['name']} ({clinic['distance_miles']} miles away) - {clinic['phone']}\n"
            
            message += "\nWhich one would you like to learn more about? Just type the number! 💫"
            
            # Create buttons for clinic selection
            buttons = []
            for i, clinic in enumerate(clinics, 1):
                title = f"{i}. {clinic['name']} - {clinic['phone']}"
                payload = f"\"{i}\""
                buttons.append({"title": title, "payload": payload})
            
            dispatcher.utter_message(text=message, buttons=buttons)
        else:
            dispatcher.utter_message(
                text=f"😔 I couldn't find any pregnancy clinics near {location} at the moment. Would you like to try a different location? I'm here to support you on your journey! 💖"
            )
        
        # Store the clinics in a slot for later reference
        return [SlotSet("available_clinics", clinics)]


class ActionGetAvailableSlots(Action):
    def name(self) -> Text:
        return "action_ask_slot_selection"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        clinic_selection = tracker.get_slot("clinic_selection")
        booking_date = tracker.get_slot("booking_date") or datetime.datetime.now().strftime("%Y-%m-%d")
        
        is_slot_available = False
        
        # Get the list of available clinics from the slot
        available_clinics = tracker.get_slot("available_clinics") or []
        
        if not available_clinics:
            dispatcher.utter_message(
                text="I don't have any clinics to show available slots for. Please search for clinics first."
            )
            return []
        
        try:
            # Convert selection to integer (1-based) and get the clinic (0-based)
            selection_idx = int(clinic_selection) - 1
            if 0 <= selection_idx < len(available_clinics):
                selected_clinic = available_clinics[selection_idx]
                clinic_id = selected_clinic["id"]
                
                # Get available slots from the database
                slots = get_available_slots(clinic_id, booking_date)
                
                if slots:
                    is_slot_available = True
                    message = f"🕒 Available appointment slots at {selected_clinic['name']} on {booking_date}:\n"
                    
                    # Create buttons for slot selection
                    buttons = []
                    for i, slot in enumerate(slots, 1):
                        # message += f"{i}. {slot['time_slot']}\n"
                        title = f"{i}. {slot['time_slot']}"
                        payload = f"\"{i}\""
                        buttons.append({"title": title, "payload": payload})
                    
                    message += "\nPlease select a slot to book your appointment."
                    
                    dispatcher.utter_message(text=message, buttons=buttons)
                else:
                    message = f"😔 I'm sorry, but there are no available slots at {selected_clinic['name']} on {booking_date}. Please try a different date."
                    dispatcher.utter_message(text=message)
                    is_slot_available = False
                
                # Store the selected clinic ID and available slots
                return [
                    SlotSet("selected_clinic_id", clinic_id),
                    SlotSet("available_slots", slots),
                    SlotSet("is_slot_available", is_slot_available)
                ]
            else:
                dispatcher.utter_message(
                    text="Invalid clinic selection. Please select a clinic from the list by number."
                )
        except (ValueError, TypeError):
            dispatcher.utter_message(
                text="Please select a clinic from the list by number."
            )
        
        return []


class ActionSelectTimeSlot(Action):
    def name(self) -> Text:
        return "action_select_time_slot"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        slot_selection = tracker.get_slot("slot_selection")
        available_slots = tracker.get_slot("available_slots") or []
        
        if not available_slots:
            dispatcher.utter_message(
                text="😅 Oops! I don't have any available slots to select from yet. Let's check what times are available first!"
            )
            return []
        
        try:
            # Convert selection to integer (1-based) and get the slot (0-based)
            selection_idx = int(slot_selection) - 1
            if 0 <= selection_idx < len(available_slots):
                selected_slot = available_slots[selection_idx]
                slot_id = selected_slot["id"]
                
                dispatcher.utter_message(
                    text=f"🌟 Perfect choice! You've selected the appointment slot at {selected_slot['time_slot']}."
                )
                
                # Store the selected slot ID
                return [SlotSet("selected_slot_id", slot_id)]
            else:
                dispatcher.utter_message(
                    text="Oops! That number doesn't match any of our time slots. Please select a time from the list by clicking a button or typing its number."
                )
        except (ValueError, TypeError):
            dispatcher.utter_message(
                text="I need a number to book your time slot. 🔢 "
                "Please select a time from the list by clicking a button or typing its number."
            )
        
        return []


# Add this after the ActionConfirmAppointment class

class ActionAskFurtherHelp(Action):
    def name(self) -> Text:
        return "action_ask_further_help"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # Reset appointment-related slots to prevent the flow from restarting
        dispatcher.utter_message(
            text="Is there anything else I can help you with today? 😊 I'm here for all your healthcare questions!"
        )
        
        # Reset slots that might trigger the appointment flow again
        return []


class ActionHandleBookingConfirmation(Action):
    def name(self) -> Text:
        return "action_handle_booking_confirmation"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        booking_confirmation = tracker.get_slot("booking_confirmation")
        slot_id = tracker.get_slot("selected_slot_id")
        user_name = tracker.get_slot("user_name") or "there"
        user_email = tracker.get_slot("user_contact_info") or "your email"
        booking_details = tracker.get_slot("booking_details") or {}
        
        if booking_confirmation:
            # User confirmed the booking, so finalize it in the database
            booking_info = f"{user_name} ({user_email})"
            booking_success = book_appointment(slot_id, booking_info)
            
            if booking_success:
                clinic_name = booking_details.get("clinic_name", "the clinic")
                appointment_date = booking_details.get("appointment_date", "the selected date")
                slot_time = booking_details.get("slot_time", "the selected time")
                
                dispatcher.utter_message(
                    text=f"Woohoo! 🎊 {user_name}, your appointment at {clinic_name} on {appointment_date} at {slot_time} has been confirmed! "
                    f"I'll send a confirmation email to {user_email} with all the details. "
                    f"Please arrive 15 minutes early and bring your ID and insurance information if applicable. "
                    f"We're looking forward to seeing you! 😊 If you need to reschedule, just let me know!"
                )
                
                # Trigger the email sending action
                return [SlotSet("is_slot_available", False), SlotSet("email_confirmation_needed", True)]
            else:
                dispatcher.utter_message(
                    text=f"Oh no! 😔 {user_name}, there was an issue booking your appointment. "
                    "The selected time slot may no longer be available. "
                    "Let's try selecting a different time slot! I'm here to help you find the perfect time. ⏰"
                )
        else:
            # User declined the booking
            dispatcher.utter_message(
                text=f"No problem, {user_name}! I've cancelled this booking request. "
                "If you'd like to try a different time or clinic, just let me know. "
                "I'm here to help whenever you're ready! 😊"
            )
        
        return [SlotSet("is_slot_available", False)]


class ActionSendAppointmentEmail(Action):
    def name(self) -> Text:
        return "action_send_appointment_email"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        user_email = tracker.get_slot("user_contact_info")
        booking_details = tracker.get_slot("booking_details") or {}
        
        if not user_email or not booking_details:
            dispatcher.utter_message(
                text="I'm missing some information needed to send your appointment confirmation email."
            )
            return []
        
        try:
            # Get email configuration from environment variables
            sender_email = os.getenv("EMAIL_SENDER")
            password = os.getenv("EMAIL_PASSWORD")
            smtp_server = os.getenv("SMTP_SERVER")
            smtp_port = int(os.getenv("SMTP_PORT"))
            
            # Create message
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = user_email
            message["Subject"] = "Your Appointment Confirmation"
            
            # Email body remains the same
            body = f"""
            <html>
            <body>
                <h2>Appointment Confirmation</h2>
                <p>Dear {booking_details.get('user_name', 'Patient')},</p>
                <p>Your appointment has been confirmed with the following details:</p>
                <ul>
                    <li><strong>Clinic:</strong> {booking_details.get('clinic_name', 'N/A')}</li>
                    <li><strong>Date:</strong> {booking_details.get('appointment_date', 'N/A')}</li>
                    <li><strong>Time:</strong> {booking_details.get('slot_time', 'N/A')}</li>
                </ul>
                <p>Please arrive 15 minutes before your appointment time with any necessary identification or insurance information.</p>
                <p>If you need to reschedule or cancel, please contact us at least 24 hours in advance.</p>
                <p>Thank you for choosing our services!</p>
                <p>Best regards,<br>The Healthcare Team</p>
            </body>
            </html>
            """
            
            message.attach(MIMEText(body, "html"))
            
            # Connect to SMTP server using environment variables
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender_email, password)
                server.send_message(message)
            
            dispatcher.utter_message(
                text=f"✅ Great news! I've sent your appointment details to {user_email}. Please check your inbox (and spam folder if needed)."
            )
            return [SlotSet("email_sent", True)]
            
        except Exception as e:
            dispatcher.utter_message(
                text=f"I encountered an issue sending your confirmation email. Please keep your booking details for reference. Error: {str(e)}"
            )
            return [SlotSet("email_sent", False),                    
            SlotSet("appointment_topic", None),
            SlotSet("booking_date", None),
            SlotSet("booking_confirmation", None),
            SlotSet("clinic_selection", None),
            SlotSet("slot_selection", None),
            SlotSet("email_confirmation_needed", None)
            ]