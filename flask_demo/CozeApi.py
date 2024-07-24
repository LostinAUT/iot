import requests
import json
import time

# 假设 self.chat_check() 方法会更新 self.chat_status
# 并且可能需要处理网络请求
max_retries = 15  # 最大重试次数
retry_delay = 8  # 两次尝试之间的延迟时间（秒）


class CozeApi:
    def __init__(self, bot_id = '', personal_access_token = ''):
        self.bot_id = bot_id

        self.personal_access_token = personal_access_token

        self.headers = {
            'Authorization': f'Bearer {personal_access_token}',
            'Content-Type': 'application/json',
        }

        self.conversation_id = ''
        self.chat_id = ''
        self.chat_status = ''

        # 获取会话ID conversation_id

        url_create = 'https://api.coze.cn/v1/conversation/create'

        response_create = requests.post(url_create, headers=self.headers)

        if response_create.status_code == 200:
            # 如果请求成功，打印返回的JSON数据
            formatted_json = json.dumps(response_create.json(), indent=4)

            # 将 JSON 字符串转换为 Python 字典
            data_dict = json.loads(formatted_json)

            # 提取 'id' 的值
            self.conversation_id = data_dict['data']['id']

            print('conversation_id:'+self.conversation_id)
        else:
            # 如果请求失败，打印错误信息
            print(f"Error: {response_create.status_code}, {response_create.text}")

    # 获取会话ID
    def conversation_create(self):
        url_create = 'https://api.coze.cn/v1/conversation/create'
        response_create = requests.post(url_create, headers=self.headers)

        if response_create.status_code == 200:
            # 如果请求成功，打印返回的JSON数据
            formatted_json = json.dumps(response_create.json(), indent=4)

            # 将 JSON 字符串转换为 Python 字典
            data_dict = json.loads(formatted_json)

            # 提取 'id' 的值
            self.conversation_id = data_dict['data']['id']
        else:
            # 如果请求失败，打印错误信息
            print(f"Error: {response_create.status_code}, {response_create.text}")


    # 创建对话
    def conversation_create(self, content):

        url_chat = f'https://api.coze.cn/v3/chat?conversation_id={self.conversation_id}'

        data_chat = {
            "bot_id": f'{self.bot_id}',
            "user_id": "123456789",
            "stream": False,
            "auto_save_history":True,
            "additional_messages":[
                {
                    "role":"user",
                    "content":content,
                    "content_type":"text"

                }
            ]
        }

        response_chat = requests.post(url_chat, headers=self.headers, json=data_chat)

        if response_chat.status_code == 200:
            
            formatted_json = json.dumps(response_chat.json(), indent=4)

            # 将 JSON 字符串转换为 Python 字典
            data_dict = json.loads(formatted_json)

            # 提取 'id' 和 'status' 的值
            self.chat_id = data_dict['data']['id']
            self.chat_status = data_dict['data']['status']
            # print(self.chat_id)
            # print(self.chat_status)
        else:
            print("对话失败")
            print(response_chat.text)

    # 查看对话状态
    def chat_check(self):
        url_chat_detail = f' https://api.coze.cn/v3/chat/retrieve?chat_id={self.chat_id}&conversation_id={self.conversation_id}'

        response_chat_detail = requests.get(url_chat_detail, headers=self.headers)

        if response_chat_detail.status_code == 200:

            formatted_json = json.dumps(response_chat_detail.json(), indent=4)
            # 将 JSON 字符串转换为 Python 字典
            data_dict = json.loads(formatted_json)

            # 提取 'status' 的值
            self.chat_status = data_dict['data']['status']
            #print(self.chat_status)
            
        else:
            print("对话失败")
            print(response_chat_detail.text)

    # 对话内容消息查看       
    def chat_detail(self):
        # 等待bot处理完毕
        for attempt in range(max_retries):
            self.chat_check()
            
            if self.chat_status == 'completed':
                break  # 如果状态变为 'completed'，则退出循环
            else:
                print(f"Chat status is not 'completed'. Retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)  # 等待一段时间再重试

        if self.chat_status != 'completed':
            print("Reached max retries without the chat status becoming 'completed'.")

        # bot处理完毕
        url_chat_message_detail = f'https://api.coze.cn/v3/chat/message/list?chat_id={self.chat_id}&conversation_id={self.conversation_id}'

        response_chat_message_detail = requests.get(url_chat_message_detail, headers=self.headers)

        if response_chat_message_detail.status_code == 200:

            formatted_json = json.dumps(response_chat_message_detail.json(), indent=4, ensure_ascii=False)
            # print(formatted_json)
            data_dict = json.loads(formatted_json)

            # 遍历数据列表，寻找 type 为 'answer' 的条目
            for item in data_dict['data']:
                if item['type'] == 'answer':
                    answer_content = item['content']
                    break
            print(answer_content)
            json_str = answer_content.strip(' ').strip('\n').strip(' ').strip('=====').strip(' ').strip('\n').strip(' ').strip('-').strip(' ')
            print(json_str)
            # 将 JSON 字符串转换为 Python 字典
            data_dict = json.loads(json_str)

            # 提取 text 和 url 的值
            text_value = data_dict['text']
            url_value = data_dict['url']

            # 输出结果
            #print(f"Text: {text_value}")
            #print(f"URL: {url_value}")
            return (text_value, url_value)

        else:
            print("查询失败")
            print(response_chat_message_detail.text)


def main():
    t = CozeApi(bot_id='7394757063139688488')
    t.conversation_create("我感到非常孤独，没有人可以聊天。你可以陪我说说话吗？")
    t.chat_check()
    (text, url) = t.chat_detail()
    print(text)
    print(url)



if __name__ == "__main__":
    print('hello, world!')
    main()            