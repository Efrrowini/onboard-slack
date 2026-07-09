import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from groq import Groq
from rag import load_and_index_handbook, search_handbook
from tracker import init_db, log_interaction, get_volunteer_stats, detect_topic, get_all_volunteers
from scheduler import start_scheduler
from rts import get_workspace_context

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

load_and_index_handbook()
init_db()

def ask_ai(question, user=None):
    context = search_handbook(question)
    workspace_context = get_workspace_context(question)

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""You are Onboard, a friendly AI volunteer onboarding assistant for HopeReach NGO.
Use the following context to answer questions accurately and helpfully.
Keep answers concise, warm, and helpful. If the answer isn't in the context, say so honestly.

VOLUNTEER HANDBOOK CONTEXT:
{context}{workspace_context}"""
            },
            {
                "role": "user",
                "content": question
            }
        ],
        max_tokens=500
    )
    return response.choices[0].message.content

@app.event("app_home_opened")
def handle_app_home(event, client):
    user = event["user"]
    stats = get_volunteer_stats(user)

    if not stats:
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "👋 Welcome to Onboard!"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Onboard* is your AI-powered volunteer onboarding assistant for HopeReach NGO.\n\nI help new volunteers get up to speed instantly — no waiting for a coordinator, no digging through documents."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Get started:*\n• Type `/onboard` in any channel\n• Mention `@Onboard` with any question\n• Ask me anything about volunteering at HopeReach!"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*What I can help with:*\n• 📋 Getting started as a volunteer\n• 🏥 Program areas and schedules\n• 📜 Policies and procedures\n• 📞 Contact information\n• 📊 Track your onboarding progress"
                }
            }
        ]
    else:
        topics_text = ", ".join(stats["topics"]) if stats["topics"] else "None yet"
        recent_text = "\n".join([f"• _{q[0]}_" for q in stats["recent_questions"]]) or "None yet"
        topic_count = len(stats["topics"])
        progress = min(int((topic_count / 4) * 100), 100)
        progress_bar = "█" * (progress // 10) + "░" * (10 - progress // 10)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🌿 Onboard — HopeReach Volunteer Assistant"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Welcome back! Here's your onboarding dashboard."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📊 Onboarding Progress*\n`{progress_bar}` {progress}%"
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
                        "text": f"*Topics Covered:*\n{topic_count}/4"
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
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Topics Covered:*\n{topics_text}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recent Questions:*\n{recent_text}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Ask me anything:*\n• _When is orientation?_\n• _What programs can I join?_\n• _Who do I contact for help?_"
                }
            }
        ]

    client.views_publish(
        user_id=user,
        view={
            "type": "home",
            "blocks": blocks
        }
    )

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
    answer = ask_ai(question, user)
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
                        "text": "📚 Answer sourced from HopeReach Volunteer Handbook + Workspace Context"
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
    topic_count = len(stats["topics"])
    progress = min(int((topic_count / 4) * 100), 100)
    progress_bar = "█" * (progress // 10) + "░" * (10 - progress // 10)

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
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Progress:*\n`{progress_bar}` {progress}%"
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
                        "text": f"*Topics Covered:*\n{topic_count}/4"
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
                    "text": f"*Topics Covered:*\n{topics_text}"
                }
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
            answer = ask_ai(question, event["user"])
            say(answer)

if __name__ == "__main__":
    start_scheduler(app)
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("Onboard is running...")
    handler.start()