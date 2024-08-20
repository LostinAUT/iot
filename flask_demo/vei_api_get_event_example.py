import datetime
import hashlib
import hmac
from urllib.parse import quote

import requests
import json

import logging

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


if __name__ == "__main__":
    now = datetime.datetime.utcnow()

    #body = {"device_id": "dv-2101105480-h5tvm@0000", "module_identifier": "default"}
    #response_body = request("POST", now, None, {}, AK, SK, "GetLastDevicePropertyValue", body)
    body = {"event_id": "669605de81558d238faadb98"}
    response_body = request("POST", now, None, {}, AK, SK, "GetMediapipeEvent", body)
    print('---')
    print(type(response_body))
    print(response_body["Result"])
