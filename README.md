# AnnotBot
Image annotation with Telegram

## How to use AnnotBot ?
1. Clone this repo
1. Install telepot (`pip install telepot`)
1. Talk with the botfather: http://telegram.me/botfather , and get a Token Key and a bot name
1. Update `config.json` with your classes and data.
1. Run `annotbot.py`
1. Browse to http://telegram.me/BOTNAME and start tagging.

## Output
Each user would have a separate json file (e.g. `12345.json`).
All data points are available for all users, if a user did not tag a data point, then its value it `""`

    {
       "image1": "",
       "image2": "sad"
    }
