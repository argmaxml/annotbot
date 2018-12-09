import sys
import time
import json
import collections
import random
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

with open("config.json", "r") as f:
    config = json.load(f)

annotated = collections.defaultdict(lambda: {k: "" for k, v in config["data"].items()})


def send_annotation_request(chat_id):
    unlabelled = [k for k, v in annotated[chat_id].items() if not any(v)]
    if len(unlabelled)==0:
        bot.sendMessage(chat_id, "Thank you, we're all done")
        return
    data_point_index = random.choice(unlabelled)
    data_point_value = config["data"][data_point_index]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=v, callback_data=f"{data_point_index}:{k}") for k, v in config["classes"].items()],
    ])
    if data_point_value.startswith("http://") or data_point_value.startswith("https://"):
        bot.sendPhoto(chat_id, data_point_value, reply_markup=keyboard)
    else:
        bot.sendMessage(chat_id, data_point_value, reply_markup=keyboard)


def on_chat_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    print(content_type, chat_type, chat_id)
    if content_type == 'text':
        bot.sendMessage(chat_id, "Hi from Annotation bot ( https://github.com/urigoren/annotbot )")
        send_annotation_request(chat_id)


def on_callback_query(msg):
    query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
    print('Callback Query:', query_id, chat_id, query_data)
    data_point, cls = query_data.split(":", 1)
    annotated[chat_id][data_point] = cls
    bot.answerCallbackQuery(query_id, text='Got ' + cls)
    send_annotation_request(chat_id)
    with open(f"{chat_id}.json", "w") as f:
        json.dump(annotated[chat_id], f, indent=4)


if __name__ == "__main__":

    bot = telepot.Bot(config["token"])
    MessageLoop(bot, {'chat': on_chat_message,
                      'callback_query': on_callback_query}
                ).run_as_thread()
    print('Listening ...')

    while 1:
        time.sleep(10)
