import os
from apscheduler.schedulers.background import BackgroundScheduler
from groq import Groq
from tracker import get_all_volunteers, get_volunteer_stats
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

def generate_checkin_question(topics):
    """Generate a personalized check-in question based on volunteer's topics"""
    topics_str = ", ".join(topics) if topics else "general volunteering"
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are Onboard, a volunteer onboarding assistant. Generate ONE short, friendly quiz question to help a volunteer review what they've learned. Keep it simple and encouraging."
            },
            {
                "role": "user",
                "content": f"Generate a review question about: {topics_str}"
            }
        ],
        max_tokens=100
    )
    return response.choices[0].message.content

def send_daily_checkins(app):
    """Send daily check-in DMs to all active volunteers"""
    print("Sending daily check-ins...")
    volunteers = get_all_volunteers()
    
    for user_id in volunteers:
        stats = get_volunteer_stats(user_id)
        if not stats or stats["total_questions"] == 0:
            continue
        
        topics = stats["topics"]
        question = generate_checkin_question(topics)
        
        try:
            app.client.chat_postMessage(
                channel=user_id,
                blocks=[
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🌅 Good Morning! Daily Check-in"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Here's your review question for today:*\n\n_{question}_"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "💡 Reply to me with your answer or ask me anything!"
                            }
                        ]
                    }
                ]
            )
            print(f"Check-in sent to {user_id}")
        except Exception as e:
            print(f"Failed to send check-in to {user_id}: {e}")

def start_scheduler(app):
    """Start the background scheduler"""
    scheduler = BackgroundScheduler()
    # Run every day at 9am
    scheduler.add_job(
        send_daily_checkins,
        'cron',
        hour=9,
        minute=0,
        args=[app]
    )
    scheduler.start()
    print("Scheduler started - daily check-ins at 9am")
    return scheduler