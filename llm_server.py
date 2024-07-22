# llm_server.py
import asyncio
import websockets
#from conversation_chain import ConversationChain
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

API_KEY = "EMPTY"
API_BASE = "http://192.168.11.101:8080/v1"
MODEL = "gpt-3.5-turbo"

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


# テンプレートの準備
template = """あなたは人間と友好的に会話するAIです。
AIはおしゃべりで、その文脈から多くの具体的な詳細を提供します。
AIが質問に対する答えを知らない場合、正直に「知らない」と言います。"""

# chatプロンプトテンプレートの準備
prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(template),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{input}")
])

from langchain.chains import ConversationChain
#from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory

# メモリの準備
memory = ConversationBufferMemory(return_messages=True)

# 会話チェーンの準備
#conversation = ConversationChain(memory=memory, prompt=prompt, llm=llm)
   
async def handle_connection(websocket, path):
    async for message in websocket:
        print(f"Received message: {message}")
        response = conversation.predict(input=message)
        await websocket.send(response)
        print(f"Sent response: {response}")

async def main():
    async with websockets.serve(handle_connection, "localhost", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    conversation = ConversationChain(memory=memory, prompt=prompt, llm=llm)  # Initialize your LLM
    asyncio.run(main())
