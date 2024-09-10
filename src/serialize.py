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
    def deserialize_message_history(data):
        messages = [
            HumanMessage(content=msg['content']) if msg['role'] == 'human' else AIMessage(content=msg['content'])
            for msg in data['messages']
        ]
        return InMemoryChatMessageHistory(messages=messages)
    
    data = json.loads(json_data)
    result = {}
    for key, value in data.items():
        if 'messages' in value:
            result[key] = deserialize_message_history(value)
        else:
            result[key] = value
    
    return result