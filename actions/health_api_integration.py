import requests
from typing import Dict, Any, Optional

def get_health_information(topic: str) -> Dict[Any, Any]:
    """
    Integrate with MedlinePlus Connect API to get health information
    """
    try:
        url = "https://connect.medlineplus.gov/service"
        params = {
            "mainSearchCriteria.v.cs": "2.16.840.1.113883.6.90",
            "mainSearchCriteria.v.c": topic,
            "knowledgeResponseType": "application/json"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def format_health_information(api_response: Dict[Any, Any]) -> Optional[str]:
    """
    Format the MedlinePlus health information into a readable message
    """
    if not api_response.get("success", False):
        return None
    
    try:
        feed = api_response["data"].get("feed", {})
        entries = feed.get("entry", [])
        
        if not entries:
            return None
        
        # Get the first entry
        entry = entries[0]
        
        formatted_info = "📚 Health Information\n\n"
        
        if "title" in entry:
            formatted_info += f"Topic: {entry['title']}\n\n"
            
        if "summary" in entry:
            formatted_info += f"Summary:\n{entry['summary']}\n\n"
            
        if "link" in entry:
            formatted_info += f"Learn more: {entry['link']}\n"
        
        formatted_info += "\nSource: MedlinePlus (National Library of Medicine)"
        return formatted_info
    except Exception:
        return None