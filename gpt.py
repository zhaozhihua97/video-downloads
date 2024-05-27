from openai import OpenAI
import tiktoken
from threading import Thread


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
      raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}.""")


def text_generation(text, model="gpt-3.5-turbo-0125"):
    # question = f"请用中文总结这段视频字幕的内容,分点进行罗列，尤其注明其中有趣的点：{text}"
    question = f"请修正这个字幕文件中的语气词，及不合适的断句，并以字幕格式返回: {text}"
    token_num = num_tokens_from_messages([{"role": "user", "content": question}])
    print(f'This video spends {token_num} tokens')

    client = OpenAI(
        base_url='https://api.openai-proxy.org/v1',
        api_key='sk-GDLcarY1fhQ3Dwy2GMa6fROTaIDnwwkieb2fJ8J4I240TaCi',
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
    print(chat_completion.choices[0].message.content)
    return chat_completion.choices[0].message.content


if __name__ == "__main__":
    file_path = "Z:\Youtube_Downloads\Sarr\SaveTwitter_subtitles.srt"
    model = "gpt-3.5-turbo-0125"

    f = open(file_path.replace('.srt', f'_{model}.srt'), 'w', encoding='utf-8')
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.read()
        question = f"请修正这个字幕文件中的语气词，及不合适的断句，请注意字幕为英语，不要翻译成中文，不需要答案前缀，只需以字幕格式返回: {lines}"
        a = text_generation(question, model=model)
        f.write(a)
