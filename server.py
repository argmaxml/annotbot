import os
import json
from sqlalchemy import create_engine
from sqlalchemy import Integer, String, Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import Flask, send_from_directory, redirect, render_template, Response, request
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import pandas as pd

debug_mode = os.name == 'nt'
with open("config.json", "r") as f:
    config = json.load(f)

if debug_mode:
    db_string = config["debug_connection_string"]
else:  # production
    db_string = config["connection_string"]
db = create_engine(db_string)

chat2dataset = {}

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

# res = db.execute("select * from annotations;")


def test_data():
    session = Session()
    session.add(Dataset(name="test", description="testing"))
    session.add(Class(dataset=1, name="positive"))
    session.add(Class(dataset=1, name="neutral"))
    session.add(Class(dataset=1, name="negative"))
    session.add(Example(dataset=1, name="ex1", value="Pump P 17.1 is used to circulate the content of vessel B 17.1 and additionally feed the column K 21. "))
    session.add(Example(dataset=1, name="ex2", value="(1) No Product flow (2) Coked pressure pipe Why (3) High temperature at the trace heating over a long time Why (4) To keep the product liquid Why (5) To keep it pumpable "))
    session.add(Annotation(dataset=1, chat_id=666, example=2, class_id=3))
    session.commit()


# --------------- BOT ---------------------- #

def send_annotation_request(chat_id):
    dataset = chat2dataset.get(chat_id)
    if type(dataset)!=int:
        raise SystemError(f"No dataset for chat_id={chat_id}")
    data_point = db.execute(
        f"""
        select E.id, E.value 
        from examples E left join annotations A on E.dataset=A.dataset and A.example=E.id 
        where A.class_id is NULL and E.dataset={dataset} 
        order by random()
        """).first()
    if data_point is None:
        bot.sendMessage(chat_id, config["done_message"])
        return
    data_point_index, data_point_value = data_point
    session = Session()
    classes = session.query(Class).filter(Class.dataset==dataset).all()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cls.name, callback_data=f"{dataset}:{data_point_index}:{cls.id}") for cls in classes],
    ])
    if data_point_value.startswith("http://") or data_point_value.startswith("https://"):
        bot.sendPhoto(chat_id, data_point_value, reply_markup=keyboard)
    else:
        bot.sendMessage(chat_id, data_point_value, reply_markup=keyboard)


def on_chat_message(msg):
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
        else:
            chat2dataset[chat_id] = dataset.id
            send_annotation_request(chat_id)


def on_callback_query(msg):
    query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
    print('Callback Query:', query_id, chat_id, query_data)
    dataset, example, cls = tuple(map(int, query_data.split(":", 2)))
    new_annotation = Annotation(dataset=dataset, chat_id=chat_id, example=example, class_id=cls)
    if debug_mode:
        print(new_annotation)
    else:
        session = Session()
        session.add(new_annotation)
        session.commit()
    bot.answerCallbackQuery(query_id, text=f"Got {cls}")
    send_annotation_request(chat_id)


# ------------- Server --------------------#


@app.route('/ann')
def get_annotations():
    session = Session()
    return str(list(session.query(Annotation).all()))


@app.route('/data/<dataset_name>')
def get_data_file(dataset_name):
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
        .pivot_table(values="cnt", aggfunc=len, index="example", columns="cls")\
        .fillna(0)\
        .to_csv()
    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=annotated.csv"})


@app.route('/bot_exists/<dataset_name>')
def bot_exists(dataset_name):
    session = Session()
    dataset = session.query(Dataset).filter(Dataset.name==dataset_name).first()
    return "0" if dataset is None else "1"


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

                           active_page="New Bot")


@app.route('/view_annotations')
def view_datasets():
    session = Session()
    return render_template("view_annotations.html",
                           pages=["Home","New Bot","View Annotations"],
                           active_page="View Annotations",
                           datasets=session.query(Dataset).all())


@app.route('/submit_dataset', methods=['GET', 'POST'])
def submit_dataset():
    form = request.form
    session = Session()
    session.add(Dataset(name=form.get("txt_botname").lower(), description=form.get("txt_desc")))
    session.commit()
    dataset_id = session.query(Dataset).filter(Dataset.name==form.get("txt_botname").lower()).first().id
    for cls in form.get("txt_classes").split('\n'):
        if any(cls.strip()):
            session.add(Class(dataset=dataset_id, name=cls.strip()))
    for datum in form.get("txt_data").split('\n'):
        if datum.find(',')>0:
            key,val = datum.strip().split(',', 1)
            session.add(Example(dataset=1, name=key, value=val))
    session.commit()
    return render_template("view_annotations.html",
                           pages=["Home","New Bot","View Annotations"],
                           active_page="View Annotations",
                           datasets=session.query(Dataset).all())


if __name__ == "__main__":
    if debug_mode:
        bot = telepot.Bot(config["token_debug"])
    else:
        bot = telepot.Bot(config["token"])
    MessageLoop(bot, {'chat': on_chat_message,
                  'callback_query': on_callback_query}
            ).run_as_thread()
    app.run(port=80, host='0.0.0.0')
