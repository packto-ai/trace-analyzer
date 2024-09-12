def convert_to_json(data):
    from langchain_core.messages import HumanMessage, AIMessage
    import json
    def serialize_message_history(history):
        return {
            'messages': [
                {
                    'role': 'human' if isinstance(msg, HumanMessage) else 'ai',
                    'content': msg.content
                }
                for msg in history.messages
            ]
        }
    
    result = {}
    for key, value in data.items():
        if hasattr(value, 'messages'):
            result[key] = serialize_message_history(value)
        else:
            result[key] = value
    
    return json.dumps(result, indent=4)


def deserialize_json(json_data):
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.chat_history import InMemoryChatMessageHistory
    import json
    chat_histories = {}
    for session_id, session_data in json_data.items():
        messages = session_data.get("messages", [])
        chat_history = InMemoryChatMessageHistory()
        for message in messages:
            role = message.get("role")
            content = message.get("content")
            if role == "human":
                chat_history.add_message(HumanMessage(content=content))
            elif role == "ai":
                chat_history.add_message(AIMessage(content=content))
        chat_histories[int(session_id)] = chat_history
    return chat_histories

JSON_SHIT = {
  "1": {
    "messages": [
      {
        "role": "human",
        "content": "What are all the protocols that you see in the trace?"
      },
      {
        "role": "ai",
        "content": "Based on the provided packet trace information, the only protocol explicitly mentioned is TCP (Transmission Control Protocol). All entries in the trace indicate TCP as the protocol being used."
      }
    ]
  }
}

# print(deserialize_json(JSON_SHIT))