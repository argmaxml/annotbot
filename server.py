import os
import json
import re
from urllib.request import urlopen
from urllib.parse import urlencode
from sqlalchemy import create_engine
from sqlalchemy import Integer, String, Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import Flask, send_from_directory, send_file, redirect, render_template, Response, request
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import pandas as pd

debug_mode = os.name == 'nt'
config_file = "config_git_ignore.json" if os.path.exists("config_git_ignore.json") else "config.json"
with open(config_file, "r") as f:
    config = json.load(f)

if debug_mode:
    db_string = config["debug_connection_string"]
else:  # production
    db_string = config["prod_connection_string"]
db = create_engine(db_string)

chat2dataset = {}
chat2last_example = {}

Base = declarative_base()
Session = sessionmaker(bind=db)


class Dataset(Base):
    __tablename__ = 'datasets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    description = Column(String)

    def __repr__(self):
        return str({"id": self.id, "name": self.name, "description": self.description})


class Class(Base):
    __tablename__ = 'classes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset = Column(Integer)
    name = Column(String)

    def __repr__(self):
        return str({"id": self.id, "name": self.name, "dataset": self.dataset})


class Example(Base):
    __tablename__ = 'examples'
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset = Column(Integer)
    name = Column(String)
    value = Column(String)

    def __repr__(self):
        return str({"id": self.id, "name": self.name, "value": self.value, "dataset": self.dataset})


class Annotation(Base):
    __tablename__ = 'annotations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset = Column(Integer)
    chat_id = Column(Integer)
    example = Column(Integer)
    class_id = Column(Integer)

    def __repr__(self):
        return str({"id": self.id, "chat_id": self.chat_id, "class_id": self.class_id, "example": self.example, "dataset": self.dataset})


Base.metadata.create_all(db)

app = Flask("annotbot")


# --------------- BOT ---------------------- #

def chunks(lst, n):
    """Yield successive n-sized chunks from lst"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def expand_regex_classes(classes, txt):
    """Replaces regex class names, with their corresponding matches"""
    new_classes = []
    for cls in classes:
        if not cls.name.startswith('/'):
            new_classes.append(cls)
            continue
        pattern, match_index = cls.name[1:].rsplit('/', 1)
        match_index = int(match_index)
        rgx = re.compile(pattern)
        matches = rgx.findall(txt)
        if match_index<len(matches):
            cls.name = matches[match_index]
            new_classes.append(cls)
    return new_classes


def send_annotation_request(chat_id):
    """Queries a datapoint, and sends annotation request via telegram"""
    dataset = chat2dataset.get(chat_id)
    if type(dataset)!=int:
        raise SystemError(f"No dataset for chat_id={chat_id}")
    data_point = db.execute(
        f"""
        select E.id, E.value from 
        (select * from examples where dataset={dataset}) E 
        left join 
        (Select * from annotations where chat_id={chat_id} and dataset={dataset}) A
         on A.example=E.id 
        where A.class_id is NULL
        order by random()
        """).first()
    if data_point is None:
        bot.sendMessage(chat_id, config["done_message"])
        return
    data_point_index, data_point_value = data_point
    session = Session()
    classes = session.query(Class).filter(Class.dataset==dataset).all()
    classes = expand_regex_classes(classes, data_point_value)
    classes_keys = [InlineKeyboardButton(text=cls.name, callback_data=f"{dataset}:{data_point_index}:{cls.id}") for cls in classes]
    control_keys = [InlineKeyboardButton(text=config["skip_text"], callback_data=config["skip_text"])]
    if 0<len(classes)<4:  # horizontally
        keyboard = InlineKeyboardMarkup(inline_keyboard=[classes_keys, control_keys])
    else:  # vertically
        keyboard = InlineKeyboardMarkup(inline_keyboard=list(chunks(classes_keys, 2)) + [control_keys])
    # Cache the last example id that was sent to this use
    chat2last_example[chat_id] = data_point_index
    if data_point_value.startswith("http://") or data_point_value.startswith("https://"):
        bot.sendPhoto(chat_id, data_point_value, reply_markup=keyboard)
    else:
        bot.sendMessage(chat_id, data_point_value, reply_markup=keyboard)


def telegram_chat_message(msg):
    """Callback for an incoming textual message"""
    content_type, chat_type, chat_id = telepot.glance(msg)
    print(content_type, chat_type, chat_id)
    if content_type == 'text':
        if debug_mode:
            chat2dataset[chat_id] = 1
            send_annotation_request(chat_id)
            return
        session = Session()
        dataset = session.query(Dataset).filter(Dataset.name==msg['text'].strip().lower()).first()
        if dataset is None:
            available_datasets = "\n" + ",".join([d.name for d in session.query(Dataset).all()])
            bot.sendMessage(chat_id, config["dataset_not_found_message"]+available_datasets)
            notify_dev(f"{chat_id} was asked to select a dataset")
        else:
            chat2dataset[chat_id] = dataset.id
            notify_dev(f"{chat_id} selected "+msg['text'].strip().lower())
            send_annotation_request(chat_id)


def telegram_callback_query(msg):
    """Callback for button click"""
    query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
    print('Callback Query:', query_id, chat_id, query_data)
    if query_data==config["skip_text"]: #Skip
        send_annotation_request(chat_id)
        return
    dataset, example, cls = tuple(map(int, query_data.split(":", 2)))
    new_annotation = Annotation(dataset=dataset, chat_id=chat_id, example=example, class_id=cls)
    if debug_mode:
        print(new_annotation)
    else:
        session = Session()
        session.add(new_annotation)
        session.commit()
    bot.answerCallbackQuery(query_id, text=f"Got {cls}")
    last_example = chat2last_example.get(chat_id, -1)
    if example==last_example:
        send_annotation_request(chat_id)


def telegram_outbound_text(token, chat_id, text):
    """Send a telegram message"""
    url = ("https://api.telegram.org/bot"+token+"/sendMessage?" + urlencode({"text": text, "chat_id": chat_id}))
    handler = urlopen(url)
    return handler.read().decode('utf-8')


def notify_dev(text):
    """Send a telegram message to dev"""
    return telegram_outbound_text(config["debug_token"], config["debug_chat_id"], text)

# ------------- Server --------------------#


@app.route('/remind')
def remind():
    ret = []
    session = Session()
    dataset2name = {d.id:d.name for d in session.query(Dataset).all()}
    token = config["debug_token"] if debug_mode else config["prod_token"]
    for chat_id, dataset_id in chat2dataset.items():
        dataset_name = dataset2name[dataset_id]
        text = f"I still have many questions about {dataset_name}, could you please help ?"
        telegram_outbound_text(token, chat_id, text)
        ret.append(f"Reminded {chat_id} about {dataset_name}")
    notify_dev("\n".join(ret))
    return '<br />'.join(ret)


@app.route('/data/<dataset_name>')
def get_data_file(dataset_name):
    """Queries the DB and returns the dataset as csv"""
    session = Session()
    dataset = session.query(Dataset).filter(Dataset.name==dataset_name).first()
    if dataset is None:
        available_datasets = "<br />" + "<br />".join([d.name for d in session.query(Dataset).all()])
        return config["dataset_not_found_message"]+available_datasets
    data = session.query(Example).filter(Example.dataset==dataset.id).all()
    csv = pd.DataFrame([(d.name, d.value) for d in data], columns=["key", "value"])\
        .to_csv()
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=data.csv"})


@app.route('/classes/<dataset_name>')
def get_classes_file(dataset_name):
    """Queries the DB and returns the classes as csv"""
    session = Session()
    dataset = session.query(Dataset).filter(Dataset.name==dataset_name).first()
    if dataset is None:
        available_datasets = "<br />" + "<br />".join([d.name for d in session.query(Dataset).all()])
        return config["dataset_not_found_message"]+available_datasets
    data = session.query(Class).filter(Class.dataset==dataset.id).all()
    csv = '\n'.join([d.name for d in data])
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=classes.csv"})


@app.route('/annotated/<dataset_name>')
def annotated(dataset_name):
    """Queries the DB and returns the annotated dataset as csv"""
    session = Session()
    dataset = session.query(Dataset).filter(Dataset.name==dataset_name).first()
    if dataset is None:
        available_datasets = "<br />" + "<br />".join([d.name for d in session.query(Dataset).all()])
        return config["dataset_not_found_message"]+available_datasets
    data = db.execute(
        f"""
            select E.name as example,C.name as cls,COUNT(DISTINCT A.chat_id) as cnt
            from examples E inner join annotations A on E.dataset=A.dataset and A.example=E.id inner join classes C on C.dataset=A.dataset and C.id=A.class_id 
            where A.dataset={dataset.id} 
            GROUP BY 1,2
            """)
    csv = pd.DataFrame(list(data), columns=["example", "cls", "cnt"])\
        .pivot_table(values="cnt", aggfunc=sum, index="example", columns="cls", fill_value=0)\
        .to_csv()
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=annotated.csv"})


@app.route('/bot_exists/<dataset_name>')
def bot_exists(dataset_name):
    """Endpoint to check if a bot name exists"""
    session = Session()
    dataset = session.query(Dataset).filter(Dataset.name==dataset_name).first()
    return "0" if dataset is None else "1"


@app.route('/favicon.ico')
def serve_favicon():
    return send_file('static/favicon.ico')


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/')
@app.route('/home')
def home():
    return render_template("home.html",
                           pages=["Home","New Bot","View Annotations"],
                           active_page="Home")


@app.route('/new_bot')
def new_dataset():
    return render_template("new_bot.html",
                           pages=["Home","New Bot","View Annotations"],
                           active_page="New Bot",
                           bot_url=config["bot_url"])


@app.route('/view_annotations')
def view_datasets():
    session = Session()
    return render_template("view_annotations.html",
                           pages=["Home","New Bot","View Annotations"],
                           active_page="View Annotations",
                           datasets=session.query(Dataset).all())


def parse_inputs(form: dict):
    """Transforms form data to python objects"""
    bot_name = form.get("txt_botname", "").lower().strip()
    bot_desc = form.get("txt_desc", "").strip()
    try:
        classes = json.loads(form.get("txt_classes", ""))
        assert type(classes) == list
    except (AssertionError, json.JSONDecodeError):
        classes = [c.strip() for c in form.get("txt_classes", "").split('\n') if any(c.strip())]
    # Regex classes
    for i in range(len(classes)-1,-1,-1):
        cls = classes[i]
        if cls.startswith('/') and cls.endswith('/'):
            try:
                rgx = re.compile(cls[1:-1])
                assert rgx.groups < 2
            except re.error:
                print (f"invalid regex {cls}")
                continue
            except AssertionError:
                print("Regex Groups are not supported")
                continue
            del classes[i]
            for j in range(config["regex_class_limit"]):
                classes.append("/{p}/{n}".format(n=j,p=rgx.pattern))

    try:
        data = json.loads(form.get("txt_data", ""))
        assert type(data) == dict
    except (AssertionError, json.JSONDecodeError):
        data = {}
        for datum in form.get("txt_data", "").split('\n'):
            if datum.find(',')<0:
                continue
            key, val = datum.split(',', 1)
            data[key] = val.replace("\\n", "\n")
    assert 2 < len(bot_name) <= 50
    assert 5 < len(bot_desc)
    assert any(data) and any(classes)
    return (bot_name, bot_desc, classes, data)


@app.route('/submit_dataset', methods=['GET', 'POST'])
def submit_dataset():
    """Creates a new dataset for the bot"""
    bot_name, bot_desc, classes, data = parse_inputs(request.form)
    session = Session()
    session.add(Dataset(name=bot_name, description=bot_desc))
    session.commit()
    dataset_id = session.query(Dataset).filter(Dataset.name==bot_name).first().id
    session.add_all([Class(dataset=dataset_id, name=cls) for cls in classes])
    session.add_all([Example(dataset=dataset_id, name=key, value=val) for key, val in data.items()])
    session.commit()
    notify_dev("New bot created: " + bot_name)
    return render_template("view_annotations.html",
                           pages=["Home","New Bot","View Annotations"],
                           active_page="View Annotations",
                           datasets=session.query(Dataset).all())


if __name__ == "__main__":
    if debug_mode:
        bot = telepot.Bot(config["debug_token"])
    else:
        bot = telepot.Bot(config["prod_token"])
    MessageLoop(bot, {
        'chat': telegram_chat_message,
        'callback_query': telegram_callback_query
    }).run_as_thread()
    app.run(port=80, host='0.0.0.0')
