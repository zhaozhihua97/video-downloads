import hashlib
import time
import uuid
import requests
import json
from datetime import datetime
import os
from tencentcloud.common.common_client import CommonClient
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from volcengine.ApiInfo import ApiInfo
from volcengine.Credentials import Credentials
from volcengine.ServiceInfo import ServiceInfo
from volcengine.base.Service import Service


class Translator():
    def __init__(self,
                 volcengine_access_key,
                 volcengine_secret_key,
                 volcengine_url,
                 tencent_secret_id,
                 tencent_secret_key,
                 tencent_endpoint,
                 youdao_APP_KEY,
                 youdao_APP_SECRET,
                 youdao_url,
                 openai_base_url,
                 openai_api_key,
                 claude_base_url,
                 claude_api_key,
                 api_usage='./api_character_count.json'
        ):
        self.volcengine_access_key = volcengine_access_key  # https://console.volcengine.com/iam/keymanage/
        self.volcengine_secret_key = volcengine_secret_key
        self.volcengine_url = volcengine_url

        self.tencent_secret_id = tencent_secret_id
        self.tencent_secret_key = tencent_secret_key
        self.tencent_endpoint = tencent_endpoint

        self.youdao_APP_KEY = youdao_APP_KEY
        self.youdao_APP_SECRET = youdao_APP_SECRET
        self.youdao_url = youdao_url

        self.openai_base_url = openai_base_url
        self.openai_api_key = openai_api_key
        self.claude_base_url = claude_base_url
        self.claude_api_key = claude_api_key


        self.data_file = api_usage

    def translate(self, api_name, sentence, target_language='zh'):
        if api_name in ['volcengine', 'tencent', 'youdao']:
            self.add_character_count(api_name, sentence)
        if api_name == 'volcengine':
            return self.volcengine_translation(sentence, target_language)
        elif api_name == 'tencent':
            return self.tencent_translation(sentence, target_language)
        elif api_name == 'youdao':
            return self.youdao_translation(sentence, target_language)
        elif api_name == 'opus':
            message = self.claude_translation(sentence, target_language, model='claude-3-opus-20240229')
            self.add_character_count(api_name, message.Usage.input_tokens+message.Usage.output_tokens)
            return message.content[0].text
        elif api_name == 'sonnet':
            return self.claude_translation(sentence, target_language, model='claude-3-sonnet-20240229')
        elif api_name == 'gpt3':
            message = self.openai_translation(sentence, target_language, model='gpt-3.5-turbo-0613')
            self.add_character_count(api_name, message[1])
            return message[0]
        elif api_name == 'gpt4':
            message = self.openai_translation(sentence, target_language, model='gpt-4-turbo-2024-04-09')
            self.add_character_count(api_name, message[1])
            return message[0]
        elif api_name == "gpt4o":
            message = self.openai_translation(sentence, target_language, model='gpt-4o-2024-05-13')
            self.add_character_count(api_name, message[1])
            return message[0]
        else:
            raise ValueError("Unsupported API")

    def openai_translation(self, sentence, target_language='zh', model="gpt-3.5-turbo-0613"):
        from openai import OpenAI
        import tiktoken
        def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
            """Returns the number of tokens used by a list of messages."""
            try:
                encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")
            if model == "gpt-3.5-turbo-0613":  # note: future models may deviate from this
                num_tokens = 0
                for message in messages:
                    num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                    for key, value in message.items():
                        num_tokens += len(encoding.encode(value))
                        if key == "name":  # if there's a name, the role is omitted
                            num_tokens += -1  # role is always required and always 1 token
                num_tokens += 2  # every reply is primed with <im_start>assistant
                return num_tokens
            else:
                raise NotImplementedError(
                    f"""num_tokens_from_messages() is not presently implemented for model {model}.""")
        question = f"请翻译这句话为{target_language}，回答不需要带有前缀: {sentence}"
        token_num = num_tokens_from_messages([{"role": "user", "content": question}])

        client = OpenAI(
            base_url=self.openai_base_url,
            api_key=self.openai_api_key,
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": question,
                }
            ],
            model=model,
        )
        return chat_completion.choices[0].message.content, token_num

    def claude_translation(self, sentence, target_language='zh', model="claude-3-sonnet-20240229"):
        import anthropic
        question = f"请翻译这句话为{target_language}，回答不需要带有前缀: {sentence}"
        client = anthropic.Anthropic(
            # defaults to os.environ.get("ANTHROPIC_API_KEY")
            base_url=self.claude_base_url,
            api_key=self.claude_api_key,
        )

        message = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0.0,
            messages=[
                {"role": "user", "content": question}
            ]
        )

        return message

    def volcengine_translation(self, sentence, target_language='zh'):
        # Assuming volcengine_translation implementation
        try:

            k_service_info = \
                ServiceInfo(self.volcengine_url,
                            {'Content-Type': 'application/json'},
                            Credentials(self.volcengine_access_key, self.volcengine_secret_key, 'translate', 'cn-north-1'),
                            5,
                            5)
            k_query = {
                'Action': 'TranslateText',
                'Version': '2020-06-01'
            }
            k_api_info = {
                'translate': ApiInfo('POST', '/', k_query, {}, {})
            }
            service = Service(k_service_info, k_api_info)
            body = {
                'TargetLanguage': target_language,
                'TextList': [sentence],
            }
            res = service.json('translate', {}, json.dumps(body))
            result = json.loads(res)
            return result['TranslationList'][0]['Translation']
        except Exception as err:
            return False

    def tencent_translation(self, sentence, target_language='zh'):
        # Assuming tencent_translation implementation
        try:
            # cred = credential.ProfileCredential().get_credential()
            cred = credential.Credential(self.tencent_secret_id,self.tencent_secret_key)

            httpProfile = HttpProfile()
            httpProfile.endpoint = self.tencent_endpoint
            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile

            params = {
                "SourceText": sentence,
                "Source": "en",
                "Target": target_language,
                "ProjectId": 0
            }
            common_client = CommonClient("tmt", "2018-03-21", cred, "ap-beijing", profile=clientProfile)
            result = common_client.call_json("TextTranslate", params)
            return result["Response"]["TargetText"]
        except TencentCloudSDKException as err:
            return False

    def youdao_translation(self, sentence, target_language='zh'):
        # Assuming youdao_translation implementation
        '''
        note: 将下列变量替换为需要请求的参数
        '''

        def doCall(url, header, params, method):
            if 'get' == method:
                return requests.get(url, params)
            elif 'post' == method:
                return requests.post(url, params, header)

        q = sentence
        lang_from = 'en'
        if target_language == 'zh':
            lang_to = 'zh-CHS'
        else:
            lang_to = target_language
        # vocab_id = '您的用户词表ID'

        data = {
            'q': q, 'from': lang_from, 'to': lang_to,
            # 'vocabId': vocab_id
        }

        addAuthParams(self.youdao_APP_KEY, self.youdao_APP_SECRET, data)

        header = {'Content-Type': 'application/x-www-form-urlencoded'}
        res = doCall(self.youdao_url, header, data, 'post')
        if res.status_code == 200:
            result = res.json()
            if "translation" not in result:
                return "Error: " + result['errorCode'] + " " + result['error_msg']
            return result['translation'][0]
        else:
            return False

    def add_character_count(self, api_name, new_chars):
        """Add character count of the new request to the correct API count and reset if it's a new month."""
        if api_name in ['volcengine', 'tencent', 'youdao']:
            len_chars = len(new_chars)
        else:
            len_chars = new_chars
        def load_or_initialize_counts():
            """Load current character counts or initialize them if not existing."""
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as file:
                    return json.load(file)
            else:
                data = {
                    "last_reset": str(datetime.now().date()),
                    "counts": {"tencent": 0, "volcengine": 0, "youdao": 0}
                }
            return data

        def save_counts(counts):
            """Save the current character counts to a JSON file."""
            with open(self.data_file, 'w') as file:
                json.dump(counts, file)

        def reset_counts_if_new_month(data):
            """Reset counts on the first of the month."""
            current_time = datetime.now().date()
            last_reset = datetime.strptime(data['last_reset'], '%Y-%m-%d').date()
            if current_time != last_reset and current_time.day == 1:
                for key in data['counts'].keys():
                    data['counts'][key] = 0
                data['last_reset'] = str(current_time)
            return data
        counts = load_or_initialize_counts()
        counts = reset_counts_if_new_month(counts)
        if api_name in counts['counts']:
            counts['counts'][api_name] += len_chars
        else:
            counts['counts'][api_name] = len_chars
        save_counts(counts)
        return counts['counts']


'''
添加鉴权相关参数 -
    appKey : 应用ID
    salt : 随机值
    curtime : 当前时间戳(秒)
    signType : 签名版本
    sign : 请求签名

    @param appKey    您的应用ID
    @param appSecret 您的应用密钥
    @param paramsMap 请求参数表
'''


def addAuthParams(appKey, appSecret, params):
    q = params.get('q')
    if q is None:
        q = params.get('img')
    q = "".join(q)
    salt = str(uuid.uuid1())
    curtime = str(int(time.time()))
    sign = calculateSign(appKey, appSecret, q, salt, curtime)
    params['appKey'] = appKey
    params['salt'] = salt
    params['curtime'] = curtime
    params['signType'] = 'v3'
    params['sign'] = sign

'''
    计算鉴权签名 -
    计算方式 : sign = sha256(appKey + input(q) + salt + curtime + appSecret)
    @param appKey    您的应用ID
    @param appSecret 您的应用密钥
    @param q         请求内容
    @param salt      随机值
    @param curtime   当前时间戳(秒)
    @return 鉴权签名sign
'''

def calculateSign(appKey, appSecret, q, salt, curtime):
    def getInput(input):
        if input is None:
            return input
        inputLen = len(input)
        return input if inputLen <= 20 else input[0:10] + str(inputLen) + input[inputLen - 10:inputLen]

    def encrypt(strSrc):
        hash_algorithm = hashlib.sha256()
        hash_algorithm.update(strSrc.encode('utf-8'))
        return hash_algorithm.hexdigest()

    strSrc = appKey + getInput(q) + salt + curtime + appSecret
    return encrypt(strSrc)


if __name__ == "__main__":
    translator = Translator()
    print(translator.translate('youdao', 'this is a test string from Tencent API request'))

