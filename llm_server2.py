import asyncio
import websockets
import json
from langchain_openai import ChatOpenAI
#from langchain_community import ChatModel
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler


API_KEY = "EMPTY"
API_BASE = "http://192.168.11.101:8080/v1"
MODEL = "gpt-3.5-turbo"

llm = ChatOpenAI(model_name=MODEL, 
                  openai_api_key=API_KEY, 
                  openai_api_base=API_BASE,
                  streaming=True, 
                  callbacks=[StreamingStdOutCallbackHandler()] ,
                  temperature=0)

async def handle_connection(websocket, path):
    async for message in websocket:
        print(f"Received message: {message}")
        try:
            # Initialize the conversation model
            # llm = ChatOpenAI(model="text-davinci-003")  # Use the correct model name
            
            def get_session_history(session_id):
                return []

            # Initialize RunnableWithMessageHistory
            conversation = RunnableWithMessageHistory(
                runnable=llm,
                get_session_history=get_session_history,
                memory={},  # Provide initial memory state if needed
                prompt="What would you like to know?"  # Initial prompt
            )
            response = conversation.run(message)
            # Send the response back to the client
            await websocket.send(response["output"])
        except Exception as e:
            print(f"connection handler failed: {e}")

async def main():
    async with websockets.serve(handle_connection, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
