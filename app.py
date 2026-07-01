import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from groq import Groq

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

# Load volunteer handbook
def load_handbook():
    with open("docs/volunteer_handbook.txt", "r") as f:
        return f.read()

HANDBOOK = load_handbook()

def ask_ai(question, user_name):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""You are Onboard, a friendly AI volunteer onboarding assistant for HopeReach NGO.
Use the following volunteer handbook to answer questions accurately and helpfully.
Keep answers concise and friendly. If the answer isn't in the handbook, say so honestly.

HANDBOOK:
{HANDBOOK}"""
            },
            {
                "role": "user",
                "content": question
            }
        ],
        max_tokens=500
    )
    return response.choices[0].message.content

@app.event("app_mention")
def handle_mention(event, say):
    user = event["user"]
    text = event["text"]
    # Remove the bot mention from the text
    question = text.split(">", 1)[-1].strip()
    if not question:
        say(f"Hey <@{user}>! Ask me anything about volunteering at HopeReach. Type `/onboard` to get started!")
        return
    say(f"<@{user}> let me check that for you...")
    answer = ask_ai(question, user)
    say(answer)

@app.command("/onboard")
def handle_onboard(ack, say, command):
    ack()
    user = command["user_id"]
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"👋 Welcome <@{user}>! I'm *Onboard*, your HopeReach volunteer assistant.\n\nI can help you with:\n• Getting started as a volunteer\n• Program areas and schedules\n• Policies and procedures\n• Contact information\n\nJust ask me anything or mention me with `@Onboard your question`!"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Quick questions to get you started:*\n• What programs can I volunteer for?\n• When is orientation?\n• What is the minimum commitment?"
                }
            }
        ]
    )

@app.command("/mystats")
def handle_mystats(ack, say, command):
    ack()
    user = command["user_id"]
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📊 *Onboarding Progress for <@{user}>*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*Status:*\nIn Progress 🔄"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Questions Asked:*\n0"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Topics Covered:*\nNone yet"
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*Next Step:*\nAttend orientation"
                    }
                ]
            }
        ]
    )

@app.event("message")
def handle_message(event, say):
    if event.get("channel_type") == "im":
        question = event.get("text", "")
        if question:
            answer = ask_ai(question, event["user"])
            say(answer)

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("Onboard is running...")
    handler.start()