from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

import asyncio
import websockets
import json

from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory

API_KEY = "EMPTY"
API_BASE = "http://192.168.11.101:8080/v1"
MODEL = "llama-2"

from langchain.prompts import (
    ChatPromptTemplate, 
    MessagesPlaceholder, 
    SystemMessagePromptTemplate, 
    HumanMessagePromptTemplate
)

llm = ChatOpenAI(model_name=MODEL, 
                 openai_api_key=API_KEY, 
                 openai_api_base=API_BASE,
                 streaming=True, 
                 callbacks=[StreamingStdOutCallbackHandler()] ,
                 temperature=0)

# Template setup
template = """
あなたは日本語で会話する高齢者介護スタッフです。あなたのプロフィールは以下です。
名前: わんこ
性別: 男
年齢: 25歳
出身: 東京都調布市
職業: 介護スタッフ（5年目）、公認介護度認定士
スキル: 長谷川式認知症診断法',
趣味: ハイキング、映画鑑賞、楽器演奏（ドラム）。
あなたは、高齢者のお世話が仕事です。特に、高齢者の悩みに対して身の上相談をして助けてあげたいと思っています。
高齢者の老化に伴う肉体的、精神的な痛みに対して、相談に乗ってあげてください。
高齢者と会話する時には、簡潔にわかりやすく答えてください。
わからない質問には、適当に答えないで、素直にわかりませんと答えてください。
自分のプロフィールについては聞かれた時だけに答えてください。また、必要なら下記のコンテクスト情報を参考にして回答してください。
"""

# Chat prompt template setup
prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(template),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{input}")
])

from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

TOKEN_LIMIT = 2000

class TruncatedConversationBufferMemory(ConversationBufferMemory):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_token_count(self, text):
        # Simple token count estimation
        return len(text.split())

    def truncate_history(self):
        total_tokens = sum(self.get_token_count(msg.content) for msg in self.messages)
        while total_tokens > TOKEN_LIMIT:
            # Remove the oldest messages until the token count is within the limit
            self.messages.pop(0)
            total_tokens = sum(self.get_token_count(msg.content) for msg in self.messages)

# Use the custom memory class
memory = TruncatedConversationBufferMemory(memory_key="history", return_messages=True)
conversation = ConversationChain(
    llm=llm,
    prompt=prompt,
    memory=memory,
)

async def handle_connection(websocket, path):
    try:
        async for message in websocket:
            print(f"Received message: {message}")
            
            # トークン数を計算し、超過する場合はトリミング
            memory.add_user_message(message)
            memory.truncate_history()

            # トリミング後のメッセージを用いて予測を生成
            response = conversation.predict(input=message)

            await websocket.send(response)
    except Exception as e:
        print(f"Connection handler failed: {e}")
    finally:
        await websocket.close()

async def main():
    async with websockets.serve(handle_connection, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
