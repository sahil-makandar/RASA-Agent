from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from actions.health_api_integration import get_health_information, format_health_information

class ActionGetHealthInformation(Action):
    def name(self) -> Text:
        return "action_get_health_information"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        health_topic = tracker.get_slot("health_topic")
        
        if not health_topic:
            dispatcher.utter_message(
                text="What health topic would you like information about?"
            )
            return []
        
        # Get information from MedlinePlus API
        api_response = get_health_information(health_topic)
        formatted_info = format_health_information(api_response)
        
        if formatted_info:
            dispatcher.utter_message(text=formatted_info)
        else:
            dispatcher.utter_message(
                text=f"I couldn't find specific information about {health_topic}."
            )
        
        return []