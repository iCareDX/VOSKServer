from operator import itemgetter
from typing import List

from langchain_openai import ChatOpenAI
#from langchain_openai.chat_models import ChatOpenAI
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import (
    RunnableLambda,
    ConfigurableFieldSpec,
    RunnablePassthrough,
)
from langchain_core.runnables.history import RunnableWithMessageHistory


class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In memory implementation of chat message history."""

    messages: List[BaseMessage] = Field(default_factory=list)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add a list of messages to the store"""
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []


# Here we use a global variable to store the chat message history.
# This will make it easier to inspect it to see the underlying results.
store = {}

def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory()
    return store[session_id]


history = get_by_session_id("1")
history.add_messages([AIMessage(content="hello")])
print(store)  # noqa: T201

#exit() # 公式サンプル終わり

# Example where the wrapped Runnable takes a dictionary input:
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

prompt = ChatPromptTemplate.from_messages([
    ("system", "You're an assistant who's good at {ability}"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])

API_KEY = "EMPTY"
API_BASE = "http://192.168.11.101:8080/v1"
MODEL = "llama-2"
llm = ChatOpenAI(model_name=MODEL, 
                  openai_api_key=API_KEY, 
                  openai_api_base=API_BASE,
                  streaming=True, 
                  callbacks=[StreamingStdOutCallbackHandler()] ,
                  temperature=0)

chain = prompt | llm

chain_with_history = RunnableWithMessageHistory(
    chain,
    # Uses the get_by_session_id function defined in the example
    # above.
    get_by_session_id,
    input_messages_key="question",
    history_messages_key="history",
)

print(chain_with_history.invoke(  # noqa: T201
    {"ability": "math", "question": "What does cosine mean?"},
    config={"configurable": {"session_id": "foo"}}
))

# Uses the store defined in the example above.
print(store)  # noqa: T201

print(chain_with_history.invoke(  # noqa: T201
    {"ability": "math", "question": "What's its inverse"},
    config={"configurable": {"session_id": "foo"}}
))

print(store)  # noqa: T201