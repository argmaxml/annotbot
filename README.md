# AnnotBot
Image annotation or Text blob annotation with Telegram.
Available on annotbot.com

## How to use AnnotBot ?
1. Goto to http://www.annotbot.com
1. Follow the instructions and create a bot
1. Chat with http://t.me/Annotbot on telegram
1. Tell it yor dataset name, and start tagging
1. Share it with as many people as possible
1. When done, goto http://www.annotbot.com/view_annotations and download the annotations

## Usage within python
1. **Install**:  `pip install -U git+https://github.com/urigoren/Annotbot`
1. **Import**: `from annotbot_client import submit_dataset, annotated`
1. **Submit**: `submit_dataset("test", "test dataset", ["a", "b", "c"], {1: "test 1", 2: "test 2"})`
1. **Download** : `annotated('test')`

## Bot Screenshot
![alt text](https://github.com/urigoren/annotbot/blob/master/static/screenshot.png "Screenshot")

## Questions / Comments / Suggestions ?
Contact me at [goren.ml](http://www.goren4u.com)
