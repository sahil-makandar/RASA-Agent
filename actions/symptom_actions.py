from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from actions.llm_utils import analyze_symptoms_with_huggingface

class ActionAnalyzeSymptoms(Action):
    def name(self) -> Text:
        return "action_analyze_symptoms"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        symptoms = tracker.get_slot("symptoms")
        
        if not symptoms:
            dispatcher.utter_message(
                text="I need to know your symptoms to analyze them. Could you please describe what you're experiencing?"
            )
            return []
        
        # Use the Hugging Face model to analyze symptoms
        analysis = analyze_symptoms_with_huggingface(symptoms)
        
        if "error" in analysis:
            dispatcher.utter_message(
                text=f"I encountered an issue analyzing your symptoms. Let me connect you with a healthcare provider instead."
            )
            return [SlotSet("appointment_recommended", True)]
        
        severity = analysis["severity_prediction"]
        recommendation = analysis["recommendation"]
        confidence = analysis["confidence"]
        
        message = f"Based on my analysis of your symptoms:\n\n"
        message += f"• Risk Level: {severity}\n"
        message += f"• Confidence: {confidence:.2%}\n"
        message += f"• Recommendation: {recommendation}\n\n"
        message += "Remember, this is not a diagnosis. Would you like to book an appointment with a healthcare provider?"
        
        dispatcher.utter_message(text=message)
        
        # Set the symptom_severity slot based on the analysis
        return [SlotSet("symptom_severity", severity)]