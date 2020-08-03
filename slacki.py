from flask import Flask
from slackify import Slackify, request, text_block, Slack, ACK, OK, block_reply, respond
import os
import json
import main_time
from slackify.tasks import async_task


app = Flask(__name__)
slackify = Slackify(app=app)
cli = Slack(os.getenv('SLACK_API_TOKEN'))


@slackify.command
def hello():
    """Send hello message with question and yes no buttons"""
    YES = 'yes'
    NO = 'no'
    yes_no_buttons_block = {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "emoji": True,
                    "text": "Yes"
                },
                "style": "primary",
                "value": "i_like_bots",
                "action_id": YES
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "emoji": True,
                    "text": "No"
                },
                "style": "danger",
                "value": "i_dont_like_bots",
                "action_id": NO
            }
        ]
    }
    blocks = [
        text_block('Do you like Bots?'),
        yes_no_buttons_block
    ]
    return block_reply(blocks)


@slackify.action("yes")
def yes(payload):
    """If a user clicks yes on the message above, execute this callback"""
    text_blok = text_block('Super! I do too :thumbsup:')
    respond(payload['response_url'], {'blocks': [text_blok]})
    return OK


@slackify.action("no")
def no(payload):
    """If a user clicks no on the hello message, execute this callback"""
    text_blok = text_block('Boo! You are so boring :thumbsdown:')
    respond(payload['response_url'], {'blocks': [text_blok]})
    return OK


@slackify.command
def fill_time():
    """Open a registration popup that asks for username and password. Don't enter any credentials!"""
    username_input_block = {
        "type": "input",
        "block_id": "username_block",
        "element": {
            "type": "plain_text_input",
            "placeholder": {
                "type": "plain_text",
                "text": "Enter your employee number"
            },
            "action_id": "username_value"
        },
        "label": {
            "type": "plain_text",
            "text": "👤 Employee number",
            "emoji": True
        }
    }
    password_input_block = {
        "type": "input",
        "block_id": "password_block",
        "element": {
            "type": "plain_text_input",
            "placeholder": {
                "type": "plain_text",
                "text": "Enter your password (usually your ID)"
            },
            "action_id": "password_value"
        },
        "label": {
            "type": "plain_text",
            "text": "🔑 Password",
            "emoji": True
        }
    }
    modal_blocks = [
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": "The application is reporting automatic hours for timewatch.co.il.\n"
                        "Currently, it check and fills the incomplete data for working days.\n"
                        "The default start time is 9am, and the duration is ~9:05",
                "emoji": True
            }
        },
        username_input_block,
        password_input_block,
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": "1. Before submitting the form, please fill your missing dates (if any)\n"
                        "2. After execution, I'm obligated to check the output in the timewatch site.\n"
                        "3. I am responsible to verify that all the data is accurate AFTER I click Fill Missing Times.",
                "emoji": True
            }
        }

    ]
    callback_id = 'registration_form'
    # The title text must be less than 25 characters
    registration_form = {
        "type": "modal",
        "callback_id": callback_id,
        "title": {
            "type": "plain_text",
            "text": "Timewatch auto-filler",
            "emoji": True
        },
        "submit": {
            "type": "plain_text",
            "text": "Fill Missing Times",
            "emoji": True
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel",
            "emoji": True
        },
        "blocks": modal_blocks
    }
    # print(json.dumps(registration_form, sort_keys=True, indent=4))
    cli.views_open(
        trigger_id=request.form['trigger_id'],
        view=registration_form
    )
    return OK


@slackify.view("registration_form")
def register_callback():
    """Handle registration form submission."""
    action = json.loads(request.form["payload"])
    response = action['view']['state']['values']
    print("redirecting to timewatch script")
    login_to_timewatch(response, action)
    # Notify user that we are handling the command, also without blocking
    text = """Your task was received and is being processed...
*MANDATORY* - login to <checkin.timewatch.co.il/punch/punch2.php|timewatch_site> and check me."""
    cli.chat_postMessage(channel=action['user']['id'], text=text)

    return ACK


@async_task
def send_message(cli, blocks, user_id):
    return cli.chat_postMessage(channel=user_id, user_id=user_id, blocks=blocks)


@async_task
def login_to_timewatch(response, action):
    username = response['username_block']['username_value']['value']
    password = response['password_block']['password_value']['value']
    tw_return = main_time.some_func('2391', username, password)
    cli.chat_postMessage(channel=action['user']['id'], text=tw_return)
    text = (f"{action['user']['real_name']} just used your filltimebot")
    print(text)
    cli.chat_postMessage(user_id='U4C0Z0QKE', text=text)


if __name__ == "__main__":
    app.run()