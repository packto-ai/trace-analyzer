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
        for message in session_data:
            sender = message.get("sender")
            content = message.get("message")

            if sender == 'Human':
                chat_output += f"You: {content}\n"
            elif sender == "Packto":
                chat_output += f"Packto: {content}\n\n"

    return chat_output


# chat = {'chat': [{'sender': 'Human', 'message': 'Hello'}, {'sender': 'Packto', 'message': 'Here are the protocols that I see in the trace:\n\n- Ethernet\n- IPv6\n- TCP\n- Raw\n- IP\n- UDP\n- ARP\n- ICMPv6 Neighbor Discovery - Router Advertisement\n- ICMPv6 Neighbor Discovery Option - Prefix Information\n- ICMPv6 Neighbor Discovery Option - Route Information Option\n- ICMPv6 Neighbor Discovery Option - Recursive DNS Server Option\n- ICMPv6 Neighbor Discovery Option - MTU\n- ICMPv6 Neighbor Discovery Option - Source Link-Layer Address\n- ICMPv6 Neighbor Discovery - Neighbor Solicitation\n- ICMPv6 Neighbor Discovery - Neighbor Advertisement\n- ICMPv6 Neighbor Discovery Option - Destination Link-Layer Address\n- DNS\n- Padding\n- IPv6 Extension Header - Hop-by-Hop Options Header\n- MLDv2 - Multicast Listener Query\n- MLDv2 - Multicast Listener Report\n- NBT Datagram Packet'}, {'sender': 'Human', 'message': 'What is the subnet the packet trace was operating on'}, {'sender': 'Packto', 'message': 'The subnet the packet trace was operating on is 192.168.1.0'}, {'sender': 'Human', 'message': 'Give me a list of all the nodes on the network and their corresponding IP addresses'}, {'sender': 'Packto', 'message': 'Here are the nodes on the network and their corresponding IP addresses:\n\n- 10:3d:1c:46:b9:46: 192.168.1.163\n- 4c:22:f3:bc:b7:18: 204.79.197.222\n- 84:ea:ed:21:1b:0c: 192.168.1.2\n- d0:bf:9c:39:c4:ed: 192.168.1.10\n- 4c:22:f3:bc:b7:1a: 0.0.0.0'}, {'sender': 'Human', 'message': 'What active TCP sessions are in the trace'}, {'sender': 'Packto', 'message': "Here are the active TCP sessions in the trace:\n\n- ('192.168.1.163', 53344, '204.79.197.222', 443)\n- ('204.79.197.222', 443, '192.168.1.163', 53344)\n- ('23.57.90.144', 443, '192.168.1.163', 53332)\n- ('192.168.1.163', 53332, '23.57.90.144', 443)\n- ('192.168.1.163', 52933, '23.57.90.144', 443)\n- ('140.82.113.25', 443, '192.168.1.163', 52635)\n- ('192.168.1.163', 53292, '34.117.35.28', 443)\n- ('34.117.35.28', 443, '192.168.1.163', 53292)\n- ('54.217.31.27', 443, '192.168.1.163', 49929)\n- ('35.186.224.30', 443, '192.168.1.163', 52601)\n- ('192.168.1.163', 52601, '35.186.224.30', 443)\n- ('44.209.32.89', 443, '192.168.1.163', 53206)\n- ('192.168.1.163', 53206, '44.209.32.89', 443)\n- ('3.168.102.8', 443, '192.168.1.163', 50447)\n- ('13.35.93.57', 443, '192.168.1.163', 50457)\n- ('52.85.61.39', 443, '192.168.1.163', 50459)\n- ('151.101.46.137', 443, '192.168.1.163', 50460)\n- ('151.101.47.10', 443, '192.168.1.163', 50470)\n- ('18.173.219.72', 443, '192.168.1.163', 50364)\n- ('34.227.36.214', 443, '192.168.1.163', 50356)\n- ('192.168.1.163', 50356, '34.227.36.214', 443)\n- ('13.35.93.71', 443, '192.168.1.163', 50365)\n- ('13.249.91.76', 443, '192.168.1.163', 50381)\n- ('34.120.195.249', 443, '192.168.1.163', 50488)\n- ('192.168.1.163', 51175, '52.202.204.11', 443)\n- ('52.202.204.11', 443, '192.168.1.163', 51175)\n- ('34.120.195.249', 443, '192.168.1.163', 49914)\n- ('20.42.73.30', 443, '192.168.1.163', 50815)\n- ('34.193.227.236', 443, '192.168.1.163', 50455)\n- ('52.5.13.197', 443, '192.168.1.163', 50456)\n- ('23.22.254.206', 443, '192.168.1.163', 50458)\n- ('13.107.13.93', 443, '192.168.1.163', 50785)\n- ('152.199.4.33', 443, '192.168.1.163', 50800)\n- ('52.5.13.197', 443, '192.168.1.163', 50378)\n- ('192.168.1.163', 51184, '54.77.70.30', 443)\n- ('54.77.70.30', 443, '192.168.1.163', 51184)"}]} 

# print(format_conversation(chat))
