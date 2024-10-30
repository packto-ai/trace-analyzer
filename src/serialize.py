#convert the result of the graph invocation which is a complicated and messy dict into json format so we can give it to the database
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
        'PCAPs': data['PCAPs'],
        'external_context': data['external_context']
    }
    
    return json.dumps(json_compatible_data, indent=4)

#once we want to update graph state, we can't give the graph json so we need to take the json from our database and put it back into the complicated
#dict format that the LangGraph is used to and update it using that
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

#Chat history is in json format which doesn't look great on a screen, so we will format it to match our needs so it looks good on the chat box
def format_conversation(chat_history):

    if chat_history is None:
        return None
    
    chat_output = ""
    
    if (chat_history == {}):
        return None

    for session_id, session_data in chat_history.items():
        for message in session_data:
            sender = message.get("sender")
            content = message.get("message")

            if sender == 'Human':
                chat_output += f"You: {content}\n"
            elif sender == "Packto":
                chat_output += f"Packto: {content}\n\n"

    return chat_output