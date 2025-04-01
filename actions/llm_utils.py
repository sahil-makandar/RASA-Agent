from transformers import pipeline

def analyze_symptoms_with_huggingface(symptoms_text):
    """Use zero-shot classification for symptom analysis"""
    try:
        classifier = pipeline("zero-shot-classification",
                            model="facebook/bart-large-mnli")
        
        # Define severity categories
        candidate_labels = ["high risk", "moderate risk", "low risk"]
        
        result = classifier(symptoms_text, candidate_labels)
        
        severity = result['labels'][0]
        confidence = result['scores'][0]
        recommendation = get_recommendation(severity)
        
        return {
            "severity_prediction": severity,
            "confidence": confidence,
            "recommendation": recommendation
        }
    except Exception as e:
        return {
            "error": str(e),
            "severity_prediction": "unknown",
            "recommendation": "Please consult with a healthcare professional for proper evaluation."
        }

def get_recommendation(severity):
    """Get recommendation based on symptom severity"""
    recommendations = {
        "high risk": "Your symptoms suggest immediate medical attention may be needed.",
        "moderate risk": "Your symptoms indicate you should seek medical care soon.",
        "low risk": "Monitor your symptoms. If they persist, consider scheduling an appointment."
    }
    return recommendations.get(severity, "Please consult with a healthcare professional for proper evaluation.")