import json
from urllib.request import urlopen, Request
from urllib.parse import urlencode
import pandas as pd

__baseurl__ = "http://www.annotbot.com"


def bot_exists(bot_name):
    url = __baseurl__ + "/bot_exists/" + urlencode({"q": bot_name}).split('=', 1)[1]
    txt = urlopen(url).read().decode('utf-8')
    return txt == "1"


def get_classes(dataset_name):
    url = __baseurl__ + "/classes/" + urlencode({"q": dataset_name}).split('=', 1)[1]
    txt = urlopen(url).read().decode('utf-8')
    return txt.split('\n')


def get_data(dataset_name):
    url = __baseurl__ + "/data/" + urlencode({"q": dataset_name}).split('=', 1)[1]
    return pd.read_csv(url, index_col=0)


def annotated(dataset_name):
    url = __baseurl__ + "/annotated/" + urlencode({"q": dataset_name}).split('=', 1)[1]
    return pd.read_csv(url, index_col=0)


def submit_dataset(dataset_name, dataset_desc, classes, data):
    if type(dataset_name) != str:
        raise TypeError("dataset_name argument should be of type `str`")
    if type(dataset_desc) != str:
        raise TypeError("dataset_desc argument should be of type `str`")
    if type(classes) != list:
        raise TypeError("classes argument should be of type `list`")
    if type(data) != dict:
        raise TypeError("data argument should be of type `dict`")
    assert 2 < len(dataset_name) <= 50
    assert 5 < len(dataset_desc)
    assert any(data) and any(classes)
    if bot_exists(dataset_name):
        raise SystemError("dataset '{d}' already exists".format(d=dataset_name))
    url = __baseurl__ + "/submit_dataset"
    req = Request(url, data=urlencode({
        "txt_botname": dataset_name,
        "txt_desc": dataset_desc,
        "txt_classes": json.dumps(classes),
        "txt_data": json.dumps(data),
    }).encode())
    res = urlopen(req)
    return res.status == 200


if __name__ == "__main__":
    print (submit_dataset("test", "test dataset", ["a", "b", "c"], {1: "test 1", 2: "test 2"}))