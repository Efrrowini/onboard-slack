import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from groq import Groq
from rag import load_and_index_handbook, search_handbook
from tracker import init_db, log_interaction, get_volunteer_stats, detect_topic
from scheduler import start_scheduler

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

# Index handbook on startup
load_and_index_handbook()
init_db()

def ask_ai(question):
    context = search_handbook(question)
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""You are Onboard, a friendly AI volunteer onboarding assistant for HopeReach NGO.
Use ONLY the following context from the volunteer handbook to answer questions.
Keep answers concise, warm, and helpful. If the answer isn't in the context, say so honestly.

CONTEXT:
{context}"""
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
    question = text.split(">", 1)[-1].strip()
    if not question:
        say(f"Hey <@{user}>! Ask me anything about volunteering at HopeReach. Type `/onboard` to get started!")
        return
    say(f"<@{user}> let me check that for you...")
    topic = detect_topic(question)
    log_interaction(user, question, topic)
    answer = ask_ai(question)
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": answer
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "📚 Answer sourced from HopeReach Volunteer Handbook"
                    }
                ]
            }
        ]
    )

@app.command("/onboard")
def handle_onboard(ack, say, command):
    ack()
    user = command["user_id"]
    say(
        blocks=[
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "👋 Welcome to HopeReach!"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Hi <@{user}>! I'm *Onboard*, your AI volunteer assistant.\n\nI can help you with:\n• Getting started as a volunteer\n• Program areas and schedules\n• Policies and procedures\n• Contact information"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Try asking me:*\n• _When is orientation?_\n• _What programs can I join?_\n• _What is the minimum commitment?_\n• _Who do I contact for help?_"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📋 View My Progress"
                        },
                        "action_id": "view_progress"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📖 Read Handbook"
                        },
                        "action_id": "read_handbook"
                    }
                ]
            }
        ]
    )

@app.command("/mystats")
def handle_mystats(ack, say, command):
    ack()
    user = command["user_id"]
    stats = get_volunteer_stats(user)

    if not stats:
        say(f"<@{user}> you haven't asked me anything yet! Type `/onboard` to get started.")
        return

    topics_text = ", ".join(stats["topics"]) if stats["topics"] else "None yet"
    recent_text = "\n".join([f"• _{q[0]}_" for q in stats["recent_questions"]]) or "None yet"

    say(
        blocks=[
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Your Onboarding Progress"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Questions Asked:*\n{stats['total_questions']} ❓"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Topics Covered:*\n{topics_text}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*First Active:*\n{stats['first_seen'][:10]} 📅"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Last Active:*\n{stats['last_active'][:10]} 🕐"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recent Questions:*\n{recent_text}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 Keep asking questions to complete your onboarding!"
                    }
                ]
            }
        ]
    )

@app.action("view_progress")
def handle_view_progress(ack, say):
    ack()
    say("Use `/mystats` to see your full onboarding progress!")

@app.action("read_handbook")
def handle_read_handbook(ack, say):
    ack()
    say("📖 The HopeReach Volunteer Handbook covers: Getting Started, Program Areas, Policies, and Contact Info. Ask me anything!")

@app.event("message")
def handle_message(event, say):
    if event.get("channel_type") == "im":
        question = event.get("text", "")
        if question:
            topic = detect_topic(question)
            log_interaction(event["user"], question, topic)
            answer = ask_ai(question)
            say(answer)

if __name__ == "__main__":
    start_scheduler(app)
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("Onboard is running...")
    handler.start()