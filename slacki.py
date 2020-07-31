import os
import random
import time
import subprocess

from flask import Flask
from slackify import (ACK, OK, Slackify, async_task, block_reply, request,
                      respond, text_block, Slack)

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
                "text": "The application is reporting automatic hours for timewatch.co.il.\nCurrently, it check and fills the incomplete data for working days.\nThe default start time is 9am, and the duration is ~9:05",
                "emoji": True
            }
        },
        username_input_block,
        password_input_block,
        {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": "1. Before submitting the form, please fill your missing dates (if any)\n2. After exectution, I'm obligated to check the output in the UI.\n3. I will verify that all the data is accurate.",
                "emoji": True
            }
        }

    ]
    callback_id = 'registration_form'
    registration_form = {
        "type": "modal",
        "callback_id": callback_id,
        "title": {
            "type": "plain_text",
            "text": "Time Watch auto filler",
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
def register_callback(payload):
    """Handle registration form submission."""
    # response = payload['view']['state']['values']
    # text_blok = text_block(f':heavy_check_mark: You are now registered.\nForm payload:\n```{response}```')
    # send_message(cli, [text_blok], payload['user']['id'])
    # send_message(cli, text_block('hiiiii'), payload['user']['id'])
    # text = f"{payload['view']['state']['values']['username_block']['username_value']['value']}, {payload['view']['state']['values']['password_block']['password_value']['value']}"
    # cli.chat_postMessage(channel=payload['user']['id'], text=text)
    print(f"main_time.py 2391 {payload['view']['state']['values']['username_block']['username_value']['value']} {payload['view']['state']['values']['password_block']['password_value']['value']}")
    # os.system(f"main_time.py 2391 {payload['view']['state']['values']['username_block']['username_value']['value']} {payload['view']['state']['values']['password_block']['password_value']['value']}")
    username = payload['view']['state']['values']['username_block']['username_value']['value']
    password = payload['view']['state']['values']['password_block']['password_value']['value']
    subprocess.call(['python', 'main_time.py']) #, '2391', username, password])
    text = "*MANDATORY* - login to <checkin.timewatch.co.il/punch/punch2.php|timewatch> and check me."
    time.sleep(5)
    cli.chat_postMessage(channel=payload['user']['id'], text=text)

    return ACK


@async_task
def send_message(cli, blocks, user_id):
    return cli.chat_postMessage(channel=user_id, user_id=user_id, blocks=blocks)


@slackify.shortcut('dice_roll')
def dice_roll(payload):
    """Roll a virtual dice to give a pseudo-random number"""
    dice_value = random.randint(1, 6)
    msg = f'🎲 {dice_value}'
    send_message(cli, blocks=[text_block(msg)], user_id=payload['user']['id'])
    return ACK


@slackify.event('reaction_added')
def echo_reaction(payload):
    """If any user reacts to a message, also react with that emoji to the message"""
    event = payload['event']
    reaction = event['reaction']
    cli.reactions_add(
        name=reaction,
        channel=event['item']['channel'],
        timestamp=event['item']['ts']
    )


@slackify.message('hello')
def say_hi(payload):
    event = payload['event']
    cli.chat_postMessage(channel=event['channel'], text='Hi! 👋')


if __name__ == "__main__":
        app.run()