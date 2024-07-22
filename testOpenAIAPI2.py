from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

API_KEY = "EMPTY"
API_BASE = "http://localhost:8000/v1"
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

messages = [
    SystemMessage(content="あなたは老人ホームの介護スタッフのWANCOです．あなたの相手は老人ホームで生活する高齢者です．優しく接しましょう．"),
    HumanMessage(content="こんにちは，腰が痛いんだけれど，どうしたらよいかアドバイスしてください．")
]
#resp = llm(messages)

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

     
# promptの中身を書き出す
for message_template in prompt.messages:
    if isinstance(message_template, SystemMessagePromptTemplate):
        print(f"SystemMessage: {message_template.prompt}")
    elif isinstance(message_template, HumanMessagePromptTemplate):
        print(f"HumanMessage: {message_template.prompt}")
    elif isinstance(message_template, MessagesPlaceholder):
        print(f"MessagesPlaceholder: {message_template.variable_name}")
        
# チャットモデルの準備
#llm = ChatOpenAI(temperature=0)

# メモリの準備
memory = ConversationBufferMemory(return_messages=True)

# 会話チェーンの準備
conversation = ConversationChain(memory=memory, prompt=prompt, llm=llm)

conversation.predict(input="鈴木太郎だけど，腰が痛いのですがどうしたらよいでしょう？")
conversation.predict(input="こんにちは")
conversation.predict(input="東京都の人口は何人ですか")

conversation.predict(input="私の名前をおぼえていますか．私はどんな状態ですか？")

# メモリの中身を取得
memory_contents = memory.chat_memory.messages
#print(memory_contents)

# メモリの内容を書き出す
for message in memory_contents:
    if isinstance(message, AIMessage):
        print(f"AI: {message.content}")
    elif isinstance(message, HumanMessage):
        print(f"Human: {message.content}")
    elif isinstance(message, SystemMessage):
        print(f"System: {message.content}")
        
   