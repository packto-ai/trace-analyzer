def convert_to_json(data):
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    import json
    def message_to_dict(message):
        if isinstance(message, HumanMessage):
            return {
                'type': 'human',
                'content': message.content,
                'id': message.id,
                'additional_kwargs': message.additional_kwargs,
                'response_metadata': message.response_metadata
            }
        elif isinstance(message, AIMessage):
            return {
                'type': 'ai',
                'content': message.content,
                'id': message.id,
                'additional_kwargs': message.additional_kwargs,
                'response_metadata': message.response_metadata,
                'tool_calls': message.tool_calls,
                'usage_metadata': message.usage_metadata
            }
        elif isinstance(message, ToolMessage):
            return {
                'type': 'tool',
                'content': message.content,
                'id': message.id,
                'tool_call_id': message.tool_call_id
            }
        else:
            raise ValueError("Unknown message type")
    
    result = {}

    converted_messages = [message_to_dict(message) for message in data['messages']]

    json_compatible_data = {
        'messages': converted_messages,
        'PCAP': data['PCAP'],
        'external_context': data['external_context']
    }
    
    return json.dumps(json_compatible_data, indent=4)


def deserialize_json(json_data):
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from langchain_core.chat_history import InMemoryChatMessageHistory
    import json
    def convert_message(message_data):
        msg_type = message_data['type']
        if msg_type == 'human':
            return HumanMessage(
                content=message_data['content'],
                additional_kwargs=message_data.get('additional_kwargs', {}),
                response_metadata=message_data.get('response_metadata', {}),
                id=message_data['id']
            )
        elif msg_type == 'ai':
            return AIMessage(
                content=message_data['content'],
                additional_kwargs=message_data.get('additional_kwargs', {}),
                response_metadata=message_data.get('response_metadata', {}),
                id=message_data['id'],
                tool_calls=message_data.get('tool_calls', []),
                usage_metadata=message_data.get('usage_metadata', {})
            )
        elif msg_type == 'tool':
            return ToolMessage(
                content=message_data['content'],
                id=message_data['id'],
                tool_call_id=message_data['tool_call_id']
            )
        else:
            raise ValueError("Unknown message type")
        
    data = None
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data

    original_messages = [convert_message(message) for message in data['messages']]

    original_data = {
        'messages': original_messages,
        'PCAP': data['PCAP'],
        'external_context': data['external_context']
    }

    return original_data

def format_conversation(chat_history):
    if chat_history is None:
        return None
    
    chat_output = ""
    
    if (chat_history == {}):
        return None

    for session_id, session_data in chat_history.items():
        messages = session_data.get("messages", [])
        
        for message in messages:
            role = message.get("role")
            content = message.get("content")
            
            if role == "human":
                chat_output += f"You: {content}\n"
            elif role == "ai":
                chat_output += f"AI: {content}\n"

    return chat_output
