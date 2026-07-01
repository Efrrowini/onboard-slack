import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])

@app.event("app_mention")
def handle_mention(event, say):
    user = event["user"]
    say(f"Hey <@{user}>! I'm Onboard, your volunteer onboarding assistant. Type `/onboard` to get started!")

@app.command("/onboard")
def handle_onboard(ack, say, command):
    ack()
    user = command["user_id"]
    say(f"Welcome <@{user}>! 👋 I'm here to help you get started as a volunteer. What would you like to know?")

@app.command("/mystats")
def handle_mystats(ack, say, command):
    ack()
    user = command["user_id"]
    say(f"<@{user}> here are your onboarding stats — coming soon!")

@app.event("message")
def handle_message(event, say):
    if event.get("channel_type") == "im":
        say("Got your message! Ask me anything about volunteering here.")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("Onboard is running...")
    handler.start()