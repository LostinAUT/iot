import requests
import json

personal_access_token = "pat_3o3jUrPKhdvDTFbgi3rm4zW0dMvWRX5cFR9Juw1wqLWXwz8Q1HMpUiJmmxJjXFRY"
bot_id = "7403553280519323700"

# 配置 Coze API 接口信息
api_url = 'https://api.coze.cn/open_api/v2/chat'
headers = {
    'Authorization': f'Bearer {personal_access_token}',
    'Content-Type': 'application/json',
    'Connection': 'keep-alive',
    'Accept': '*/*'
}

# 配置请求体
data = {
    'bot_id': bot_id,  # 替换为你的 Bot ID
    'user': '123',
    'query': '今天的天气怎么样？',
    'stream': False
}


def coze_chat():
    # 发起对话请求
    response = requests.post(api_url, headers=headers, json=data)

    # 检查响应状态码
    if response.status_code == 200:
        # 解析响应内容
        response_data = response.json()
        # data1 = json.loads(response_data)

        # # 初始化存储 text 和 url 的变量
        # text_content = None
        # url_content = None
        #
        # # 遍历 messages 列表
        # for message in data1['messages']:
        #     if message['type'] == 'answer':
        #         # 解析 content 字段的 JSON 字符串
        #         content_data = json.loads(message['content'].lstrip('- '))
        #         text_content = content_data.get('text')
        #         url_content = content_data.get('url')
        #         break
        #
        # print(f"Text: {text_content}")
        # print(f"URL: {url_content}")

        # print(f"Conversation ID: {response_data['conversation_id']}")
        # print(f"Status: {response_data['msg']}")
        #
        # print(f"{response_data['messages'][0]['content']}")

        print('-' * 40)
        # for message in response_data['messages']:
        #     print("-"*40)
        #     print(f"{message['content']}")
        print("Response from Coze:")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        print('-' * 40)
        print(response_data)
        print('-' * 40)

        for message in response_data['messages']:
            if message['type'] == 'answer':
                print(message['content'])
                break

        print(response_data['messages'][0]['content'])
    else:
        print("Failed to connect to Coze API:", response.status_code)


# 调用函数
coze_chat()
