import eventlet
eventlet.monkey_patch()
from flask_socketio import SocketIO
from flask import Flask, render_template, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import datetime
import hashlib
import hmac
from urllib.parse import quote
import requests
import json
import logging
import re
import subprocess
import base64
import uuid
import time
from asr import test_one


app = Flask(__name__)
socketio = SocketIO(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///health_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)


class HealthData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    heart_rate = db.Column(db.Integer)
    spo2 = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)

    def __init__(self, heart_rate, spo2, temperature, humidity):
        self.heart_rate = heart_rate
        self.spo2 = spo2
        self.temperature = temperature
        self.humidity = humidity


# 创建数据库和表
with app.app_context():
    db.create_all()


try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client
http_client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

# 以下参数视服务不同而不同，一个服务内通常是一致的
Service = "vei_api"
Version = "2022-01-01"
Region = "cn-beijing"
Host = "open.volcengineapi.com"
ContentType = "application/json"

# 请求的凭证，从IAM或者STS服务中获取
AK = "AKLTOThkN2ZjNWQyNWZhNGU5NjhmN2RiYWQzYWI2NTY1ZDc"
SK = "TWpFeU1HWTFObVkzTWpsbE5HRXdNbUl5WWpjM01HSXhNbVJsWVRnNE1EYw=="
# 当使用临时凭证时，需要使用到SessionToken传入Header，并计算进SignedHeader中，请自行在header参数中添加X-Security-Token头
# SessionToken = ""

# personal_access_token = "pat_O7P0vcg1Bw1Zb0MpPyYbleeInHnmgoKJ9dkNjtIWJeuY2Qoi8KD7oKzURqYRK96t"
personal_access_token = "pat_3o3jUrPKhdvDTFbgi3rm4zW0dMvWRX5cFR9Juw1wqLWXwz8Q1HMpUiJmmxJjXFRY"
bot_id = "7403665899993284648"
# bot_ids = ["7403553280519323700", "7403665899993284648"]

# 配置 Coze API 接口信息
api_url = 'https://api.coze.cn/open_api/v2/chat'
headers = {
    'Authorization': f'Bearer {personal_access_token}',  # 替换为你的个人访问令牌
    'Content-Type': 'application/json',
    'Connection': 'keep-alive',
    'Accept': '*/*'
}

# 语音合成
# 填写平台申请的appid, access_token以及cluster
appid = "6228786254"
access_token= "6WnF4rwIiS76sOgOHJqyfBFq1j9swTfX"
cluster = "volcano_tts"

voice_type = "BV009_streaming"
host = "openspeech.bytedance.com"
tts_api_url = f"https://{host}/api/v1/tts"

header = {"Authorization": f"Bearer;{access_token}"}


def norm_query(params):
    print("params: ", params)
    query = ""
    for key in sorted(params.keys()):
        if type(params[key]) == list:
            for k in params[key]:
                query = (
                        query + quote(key, safe="-_.~") + "=" + quote(k, safe="-_.~") + "&"
                )
        else:
            query = (query + quote(key, safe="-_.~") + "=" + quote(params[key], safe="-_.~") + "&")
    query = query[:-1]
    return query.replace("+", "%20")


# 第一步：准备辅助函数。
# sha256 非对称加密
def hmac_sha256(key: bytes, content: str):
    return hmac.new(key, content.encode("utf-8"), hashlib.sha256).digest()


# sha256 hash算法
def hash_sha256(content: str):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# 第二步：签名请求函数
def request(method, date, query, header, ak, sk, action, body):
    # 第三步：创建身份证明。其中的 Service 和 Region 字段是固定的。ak 和 sk 分别代表
    # AccessKeyID 和 SecretAccessKey。同时需要初始化签名结构体。一些签名计算时需要的属性也在这里处理。
    # 初始化身份证明结构体
    credential = {
        "access_key_id": ak,
        "secret_access_key": sk,
        "service": Service,
        "region": Region,
    }
    # 初始化签名结构体
    if query is None:
        send_query = {"Action": action, "Version": Version}
    else:
        send_query = {"Action": action, "Version": Version, **query}

    request_param = {
        "body": body,
        "host": Host,
        "path": "/",
        "method": method,
        "content_type": ContentType,
        "date": date,
        "query": send_query
    }
    if body is None:
        request_param["body"] = ""
    else:
        request_param["body"] = json.dumps(request_param["body"])
    # 第四步：接下来开始计算签名。在计算签名前，先准备好用于接收签算结果的 signResult 变量，并设置一些参数。
    # 初始化签名结果的结构体
    x_date = request_param["date"].strftime("%Y%m%dT%H%M%SZ")
    short_x_date = x_date[:8]
    x_content_sha256 = hash_sha256(request_param["body"])
    sign_result = {
        "Host": request_param["host"],
        "X-Content-Sha256": x_content_sha256,
        "X-Date": x_date,
        "Content-Type": request_param["content_type"],
    }
    # 第五步：计算 Signature 签名。
    signed_headers_str = ";".join(
        ["content-type", "host", "x-content-sha256", "x-date"]
    )
    # signed_headers_str = signed_headers_str + ";x-security-token"
    canonical_request_str = "\n".join(
        [request_param["method"].upper(),
         request_param["path"],
         norm_query(request_param["query"]),
         "\n".join(
             [
                 "content-type:" + request_param["content_type"],
                 "host:" + request_param["host"],
                 "x-content-sha256:" + x_content_sha256,
                 "x-date:" + x_date,
             ]
         ),
         "",
         signed_headers_str,
         x_content_sha256,
         ]
    )

    # 打印正规化的请求用于调试比对
    print("canonical_request_str", canonical_request_str)
    hashed_canonical_request = hash_sha256(canonical_request_str)

    # 打印hash值用于调试比对
    print("hashed_canonical_request", hashed_canonical_request)
    credential_scope = "/".join([short_x_date, credential["region"], credential["service"], "request"])
    string_to_sign = "\n".join(["HMAC-SHA256", x_date, credential_scope, hashed_canonical_request])

    # 打印最终计算的签名字符串用于调试比对
    print("string_to_sign", string_to_sign)
    k_date = hmac_sha256(credential["secret_access_key"].encode("utf-8"), short_x_date)
    k_region = hmac_sha256(k_date, credential["region"])
    k_service = hmac_sha256(k_region, credential["service"])
    k_signing = hmac_sha256(k_service, "request")
    signature = hmac_sha256(k_signing, string_to_sign).hex()

    sign_result["Authorization"] = "HMAC-SHA256 Credential={}, SignedHeaders={}, Signature={}".format(
        credential["access_key_id"] + "/" + credential_scope,
        signed_headers_str,
        signature,
    )
    print("sign_result", sign_result)
    header = {**header, **sign_result}
    # header = {**header, **{"X-Security-Token": SessionToken}}
    # 第六步：将 Signature 签名写入 HTTP Header 中，并发送 HTTP 请求。
    url = "https://{}{}".format(request_param["host"], request_param["path"])
    r = requests.request(method=method,
                         url=url,
                         headers=header,
                         params=request_param["query"],
                         data=request_param["body"],
                         )
    print("r.text", r.text)
    return r.json()


# 使用正则表达式提取数值
def extract_value(data, key):
    match = re.search(f"{key}: ([\d.-]+)", data)
    if match:
        return match.group(1)
    return 'N/A'


def fetch_health_data():
    heart_rate, spo2, temperature, humidity = 60, 70, 25, 60
    while True:
        # now = datetime.datetime.utcnow()
        # body = {
        #     "device_id": "dv-2101557672-47f8f@0000",
        #     "module_identifier": "身体状态"
        # }
        # response_body = request("POST", now, None, {}, AK, SK, "GetLastDevicePropertyValue", body)
        # items = response_body.get("Result", {}).get("items", [])
        #
        # # 初始化数据
        # heart_rate = spo2 = temperature = humidity = 'N/A'
        #
        # # 提取数据
        # for item in items:
        #     value = item.get("value", "")
        #     if "Heart Rate" in value:
        #         heart_rate = extract_value(value, "Heart Rate")
        #         spo2 = extract_value(value, "SPO2")
        #     if "Temperature" in value:
        #         temperature = extract_value(value, "Temperature")
        #         humidity = extract_value(value, "Humidity")
        #
        # # 存储到数据库
        # if heart_rate != 'N/A':
        #     new_data = HealthData(heart_rate=heart_rate, spo2=spo2, temperature=temperature, humidity=humidity)
        #     db.session.add(new_data)
        #     db.session.commit()
        #

        heart_rate += 1
        spo2 += 1
        temperature += 1
        humidity += 1

        # 发送数据到客户端
        socketio.emit('update_data', {
            'heart_rate': float(heart_rate),
            'spo2': float(spo2),
            'temperature': float(temperature),
            'humidity': float(humidity)
        })

        # 每2秒更新一次
        socketio.sleep(1)


@app.route('/')
def index():
    now = datetime.datetime.utcnow()
    body = {"page_index": 1, "page_size": 10}
    response_body = request("POST", now, None, {}, AK, SK, "ListMediapipeEvent", body)
    # url = response_body["Result"]["items"][0]["image_url"]
    items = response_body.get("Result", {}).get("items", [])

    url1, url2 = '', ''
    count = 0
    for item in items:
        if count == 2:
            break
        if "obj_bboxes" in item:
            for bbox in item["obj_bboxes"]:
                if bbox.get("label") == "down":
                    url1 = item["image_url"]
                    count += 1
                    print(url1)
                if bbox.get("label") == "fighting":
                    url2 = item["image_url"]
                    count += 1
                    print(url2)

    return render_template('index.html', url1=url1, url2=url2)


@socketio.on('connect')
def handle_connect():
    socketio.start_background_task(fetch_health_data)


@app.route('/data1')
def get_data():
    health_data = HealthData.query.order_by(HealthData.timestamp).limit(10).all()
    data_list = [{
        'heart_rate': d.heart_rate,
        'spo2': d.spo2,
        'temperature': d.temperature,
        'humidity': d.humidity,
        'timestamp': d.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for d in health_data]
    return jsonify(data_list)


@app.route('/start-recording', methods=['POST'])
def start_recording():
    try:
        # 调用录音Python文件
        result = subprocess.run(['python', 'audio.py'], capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({"status": "success", "message": "Recording started"}), 200
        else:
            print(f"Error: {result.stderr}")
            return jsonify({"status": "error", "message": result.stderr}), 500
    except Exception as e:
        print(f"Exception: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    query = test_one()
    data = {
        'bot_id': bot_id,
        'user': '123',
        'query': query,
        'stream': False
    }
    # 发起对话请求
    response = requests.post(api_url, headers=headers, json=data)
    # 检查响应状态码
    if response.status_code == 200:
        # 解析响应内容
        response_data = response.json()
        reply = ''
        for message in response_data['messages']:
            if message['type'] == 'answer':
                reply = message['content']
                print(reply)
                break
        request_json = {
            "app": {
                "appid": appid,
                "token": "access_token",
                "cluster": cluster
            },
            "user": {
                "uid": "388808087185088"
            },
            "audio": {
                "voice_type": voice_type,
                "encoding": "mp3",
                "speed_ratio": 1.0,
                "volume_ratio": 1.0,
                "pitch_ratio": 1.0,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": reply,
                "text_type": "plain",
                "operation": "query",
                "with_frontend": 1,
                "frontend_type": "unitTson"
            }
        }
        try:
            resp = requests.post(tts_api_url, json.dumps(request_json), headers=header)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            tts_path = f"./static/audio/{timestamp}.mp3"
            # print(f"resp body: \n{resp.json()}")
            if "data" in resp.json():
                data = resp.json()["data"]
                file_to_save = open(tts_path, "wb")
                file_to_save.write(base64.b64decode(data))
        except Exception as e:
            e.with_traceback()

        return jsonify({'query': query, 'reply': reply, 'tts_path': tts_path})
    else:
        print("Failed to connect to API:", response.status_code)


@app.route('/static/audio/<filename>')
def send_audio(filename):
    return send_from_directory('static/audio', filename)


if __name__ == '__main__':
    # app.run(debug=True)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
