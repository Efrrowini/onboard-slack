import os
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

client = WebClient(token=os.environ["SLACK_USER_TOKEN"])
def search_workspace(query, count=3):
    """Search workspace messages using Slack's Real-Time Search API"""
    try:
        result = client.search_messages(
            query=query,
            count=count,
            sort="relevance"
        )
        
        messages = result.get("messages", {}).get("matches", [])
        
        if not messages:
            return None
        
        context_parts = []
        for msg in messages:
            text = msg.get("text", "").strip()
            channel = msg.get("channel", {}).get("name", "unknown")
            if text and len(text) > 10:
                context_parts.append(f"[#{channel}]: {text}")
        
        if not context_parts:
            return None
            
        return "\n".join(context_parts[:3])
    
    except Exception as e:
        print(f"RTS search error: {e}")
        return None

def get_workspace_context(question):
    """Get relevant workspace context for a question"""
    context = search_workspace(question)
    if context:
        return f"\n\nRELEVANT WORKSPACE CONTEXT:\n{context}"
    return ""

if __name__ == "__main__":
    result = search_workspace("volunteer orientation")
    print("RTS Result:", result)