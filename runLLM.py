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

#messages = [
#    SystemMessage(content="あなたは老人ホームの介護スタッフのWANCOです．あなたの相手は老人ホームで生活する高齢者です．優しく接しましょう．"),
#    HumanMessage(content="こんにちは，腰が痛いんだけれど，どうしたらよいかアドバイスしてください．")
#]
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

# メモリの準備
memory = ConversationBufferMemory(return_messages=True)

# 会話チェーンの準備
conversation = ConversationChain(memory=memory, prompt=prompt, llm=llm)
   
def chat_with_LLM(text):
    result = None  # 初期化
    result = conversation.predict(input=text)
    return str(result)

if __name__ == "__main__":
    print("SYSTEM: チャットを開始します。終了するには '/exit' を入力してください。")

    while True:
        user_input = input("USER: ")
        if user_input == '/exit':
            print("SYSTEM: チャットを終了します。")
            break

        # GPT-3による応答を取得
        assistant_reply = chat_with_LLM(user_input)

        # モデルの応答を表示
        print("GPT: " + assistant_reply)