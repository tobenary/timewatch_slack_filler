import json
import logging
import os
import main_time
import re
from datetime import date
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")  # used for socket mode.
# from slack_bolt.oauth.oauth_settings import OAuthSettings

logger = logging.getLogger("fill_time_bolt")
logging.basicConfig(
    level=logging.INFO,
    format=("%(asctime)s %(thread)d [%(levelname)s|%(name)s|%(funcName)s] "
            "%(message)s"),
    handlers=[logging.FileHandler(os.path.join(os.getcwd(), "2023_fill_time_bolt.log")),
              logging.StreamHandler()])

app = App(
    signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
    token=os.getenv("SLACK_BOT_TOKEN")

    # OAuth
    # oauth_settings=OAuthSettings(
    #     client_id=os.getenv("SLACK_CLIENT_ID"),
    #     client_secret=os.getenv("SLACK_CLIENT_SECRET"),
    #     scopes=["app_mentions:read", "channels:history",
    #             "im:history", "chat:write", "commands"],
    # )
)


@app.event("app_mention")
def reply_to_mention(event, client):
    """
    You can listen to any Events API event using the event()
    listener after subscribing to it in your app configuration.

    Note: your app *must* be present in the channels where it
    is mentioned.

    Please see the 'Event Subscriptions' and 'OAuth & Permissions'
    sections of your app's configuration to add the following for
    this example to work:

    Event subscription(s):   app_mentioned, messages.channels
    Required scope(s):       app_mentions:read, chat:write

    Further Information & Resources
    https://slack.dev/bolt-python/concepts#event-listening
    https://api.slack.com/events
    """

    try:
        text = f"Thanks for the mention, <@{event['user']}>! I can help you with filling your " \
               f"missing times by typing\n`/fill_time` at the message bar"
        # client.chat_postMessage(channel=event['channel'], text=text)
        client.chat_postEphemeral(channel=event['channel'], text=text, user=event['user'])
    except Exception as e:
        logger.error(f"Error responding to app_mention: {e}")


# @app.message("hello")
@app.message(re.compile("^(fill_time|hi|hello|hey|help|\?)", flags=re.IGNORECASE))
# regular expression matches are inside of context.matches
def reply_to_keyword(message, say, context):
    """
    Messages can be listened for, using specific words and phrases.
    message() accepts an argument of type str or re.Pattern object
    that filters out any messages that does not match the pattern.

    Note: your app *must* be present in the channels where this
    keyword or phrase is mentioned.

    Please see the 'Event Subscriptions' and 'OAuth & Permissions'
    sections of your app's configuration to add the following for
    this example to work:

    Event subscription(s):  message.channels
    Required scope(s):      channels:history, chat:write

    Further Information & Resources
    https://slack.dev/bolt-python/concepts#message-listening
    https://api.slack.com/messaging/retrieving
    """
    print(context['matches'])
    if len(context['matches']) == 0:
        return

    try:

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Hola! This is just a test that everything works correctly!\nYou can "
                            "fill your missing times by typing `/fill_time` at the message bar"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Click Button",
                    },
                    "value": "button_value",
                    "action_id": "first_button"
                }
            }
        ]
        say(text="type `fill_time`", blocks=blocks)
        return

    except Exception as e:
        logger.error(f"Error responding to message keyword 'hello': {e}")


@app.action("first_button")
def respond_to_button_click(action, ack, say):
    """
    Interactivity is all about action taken by the user! Actions
    can be filtered using an `action_id`, which acts as unique
    identifier for interactive components on the Slack platform.

    Note: you *must* subscribe to Interactivity to receive actions.

    Please see the 'Event Subscriptions' and 'OAuth & Permissions'
    sections of your app's configuration to add the following for
    this example to work:

    Event subscription(s):  none
    Required scope(s):      chat:write

    Further Information & Resources
    https://slack.dev/bolt-python/concepts#action-listening
    https://api.slack.com/interactivity
    """
    ack()
    try:
        say("You clicked the button! Yeah!")
    except Exception as e:
        logger.error(f"Error responding to 'first_button' button click: {e}")


# @app.shortcut("fill_time")
@app.command("/fill_time")
def open_modal(ack, command, client):
    """
    Shortcuts are invokable entry points to apps. Global shortcuts
    are available from within search in Slack and message shortcuts
    are available in the context menus of messages.

    Note: you *must* subscribe to Interactivity to enable shortcuts.

    Please see the 'Event Subscriptions' and 'OAuth & Permissions'
    sections of your app's configuration to add the following for
    this example to work:

    Event subscription(s):  none
    Required scope(s):      commands

    Further Information & Resources
    https://slack.dev/bolt-python/concepts#shortcuts
    https://api.slack.com/interactivity/shortcuts
    """
    ack()
    today = date.today()
    year = today.year
    month = today.month
    try:
        fill_time_modal = json.load(open("fill_time_modal.json", "r", encoding="utf8"))
        fill_time_modal["private_metadata"] = command['channel_id']

        desired_text = (
            f"The application is reporting automatic hours for timewatch.co.il.\n"
            f"Currently, it check and fills the incomplete data for working days.\n"
            f"The default start time is 9am, and the duration is ~9:05\n\n"
            f"The current dates for *this month* are *21/{month - 1}/{year} til the 20/{month}/{year}*\n"
            f"The 'calculated' month is the current month we're at (so, don't execute the bot for "
            f"`01/{month + 1}/{year}` in `27/{month}/{year}`...)")

        for block in fill_time_modal["blocks"]:
            if '*to be replaced with dates*' in block.get("text").get("text"):
                block["text"] = {
                    "type": "mrkdwn",
                    "text": desired_text
                }
                break

        # print(json.dumps(fill_time_modal, sort_keys=True, indent=4))
        client.views_open(
            trigger_id=command["trigger_id"],
            view=fill_time_modal
        )
    except Exception as e:
        logger.error(f"Error opening modal: {e}")


# Handle a view_submission event
@app.view("Fill_Missing_Times")
def handle_submission(ack, body, client, view):
    username = view["state"]["values"]['username_block']['username_value']['value']
    password = view["state"]["values"]['password_block']['password_value']['value']
    slack_user_id = body["user"]["id"]
    d = str(view['state']['values'].values())
    count = d.count('value-')

    # Validate the inputs
    errors = {}
    if len(password) < 3:
        errors["password_block"] = "The value must be longer than 2 characters"
    if len(username) < 2:
        errors['username_block'] = "Come on...You forgot the main part?"

    if count != 3:
        view['state']['values'].pop('username_block')
        view['state']['values'].pop('password_block')
        dictionary_key = view['state']['values'].keys()
        errors[list(dictionary_key)[0]] = "select all"

    if len(errors) > 0:
        ack(response_action="errors", errors=errors)
        return
    # Acknowledge the view_submission event and close the modal
    ack()

    # Do whatever you want with the input data.
    # then sending the user a verification of their submission
    # login_to_timewatch(username, password, slack_user_id, client)
    # Message to send user
    msg = ""
    try:
        # Execute the Time watch script and notify the user.
        msg = ("Your task was received and is being processed...\n"
               "It should take approximately *4 minutes* maximum.\n"
               "If you have not got another slack notification from me, "
               "please tell the creator for a bug fix.")

    except Exception as e:
        msg = "There was an error with your submission"
        logger.error(f"Error responding to 'Fill Missing Times' button click: {e}")

    finally:
        # Message the user
        try:
            client.chat_postEphemeral(channel=view['private_metadata'], text=msg,
                                      user=slack_user_id, link_names=True)
        except Exception:
            client.chat_postMessage(channel=slack_user_id, text=msg, link_names=True)
        login_to_timewatch(username, password, slack_user_id, client)


def login_to_timewatch(user_id, password, slack_user_id, client):
    username = user_id
    password = password
    tw_return = main_time.some_func('2391', username, password)
    client.chat_postMessage(channel=slack_user_id, text=tw_return)
    # if 'failed!' in tw_return:
    #     text = f"FYI, <@{slack_user_id}> just used your filltimebot with wrong password"
    #     client.chat_postMessage(channel='U4C0Z0QKE', text=text, link_names=True)


@app.event("app_home_opened")
def publish_home_view(client, event):
    """
    The Home tab is a persistent, yet dynamic interface for apps.
    The user can reach the App Home from the conversation list
    within Slack or by clicking on the app's name in messages.

    Note: you *must* enable Home Tab (App Home > Show Tabs Section)
    to receive this event.

    Please see the 'Event Subscriptions' and 'OAuth & Permissions'
    sections of your app's configuration to add the following:

    Event subscription(s):  app_home_opened
    Required scope(s):      none

    Further Information & Resources
    https://slack.dev/bolt-python/concepts#app-home
    https://api.slack.com/surfaces/tabs
    """

    try:
        home_modal = json.load(open("home_modal.json", "r", encoding="utf8"))
        desired_text = f"*Welcome to my app home, <@{event['user']}> :house:*"

        for block in home_modal["blocks"]:
            if not block.get("text").get("text"):
                block["text"] = {
                    "type": "mrkdwn",
                    "text": desired_text
                }
                break
        client.views_publish(
            user_id=event["user"],
            view=home_modal
        )

    except Exception as e:
        logger.error(f"Error publishing view to Home Tab: {e}")


@app.error
def handle_bad_request(error, body, logger):
        print(error)
        logger.exception(f"Error: {error}")
        logger.info(f"Request body: {body}")
        # return 'bad request!', 400

if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
