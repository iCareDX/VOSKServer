import argparse
import json
from operator import itemgetter
from typing import List
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnableLambda, ConfigurableFieldSpec, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory

API_KEY = "EMPTY"
API_BASE = "http://192.168.11.101:8080/v1"
MODEL = "llama-2"
llm = ChatOpenAI(model_name=MODEL, 
                  openai_api_key=API_KEY, 
                  openai_api_base=API_BASE,
                  streaming=True, 
                  callbacks=[StreamingStdOutCallbackHandler()] ,
                  temperature=0)

class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In memory implementation of chat message history."""

    messages: List[BaseMessage] = Field(default_factory=list)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add a list of messages to the store"""
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

# Here we use a global variable to store the chat message history.
store = {}

def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory()
    return store[session_id]

def main():
    parser = argparse.ArgumentParser(description="Basic Chat Program")
    parser.add_argument('-c', '--chat_session', type=str, default="chat", help="Chat session ID")
    parser.add_argument('-m', '--llm_model', type=str, default="gpt-3.5-turbo", help="LLM model to use")
    args = parser.parse_args()

    chat_session = args.chat_session
    llm_model = args.llm_model

    history = get_by_session_id(chat_session)
    
    llm = ChatOpenAI(model_name=MODEL, 
            openai_api_key=API_KEY, 
            openai_api_base=API_BASE,
            streaming=True, 
            callbacks=[StreamingStdOutCallbackHandler()],
            temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "あなたは、各分野の専門家として、ユーザーの入力に対し、以下の条件を守って、わかりやすく解説します。条件：\n 1.出力は、平易な日本語の平文、スライド、プログラムコードからなります。\n 2.スライドは、VS CodeのMarp extensionで確認するので、そのまま使えるmarkdown形式で出力してください。\n 3.プログラムコードは、特に指定がなければpythonで出力してください。\n 4.その他、特にプロンプトで指定された場合は、その指示に従ってください。"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])

    chain = prompt | llm

    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_by_session_id,
        input_messages_key="question",
        history_messages_key="history",
    )

    while True:
        user_input = input("あなた: ")
        if user_input.lower() == "exit":
            break

        response = chain_with_history.invoke(
            {"question": user_input},
            config={"configurable": {"session_id": chat_session}}
        )

        # Get the latest AI response
        latest_response = store[chat_session].messages[-1].content
        print("AI: ", latest_response)

    # Save chat history to a JSON file
    filename = f"log_{chat_session}.json"
    chat_log = [
        {"human": msg.content} if isinstance(msg, BaseMessage) else {"AI": msg.content} 
        for msg in store[chat_session].messages
    ]

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(chat_log, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
    