import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet
import requests

#@tool
def network_nodes(PCAP: str) -> list:
    """
    Tool to find any information about a specific 
    nodes in the network the trace was done on 
    or questions about specific MAC addresses
    or specific devices on the network.
    """

    # Load the pcapng file
    capture = pyshark.FileCapture(PCAP)

    mac_addresses = []
    nodes = []


    for packet in capture:
        if 'eth' in packet:
            if (packet.eth.src not in mac_addresses):
                mac_addresses.append(packet.eth.src)
            if (packet.eth.dst not in mac_addresses):
                mac_addresses.append(packet.eth.dst)

    print(mac_addresses)

    
    for mac_address in mac_addresses:
        print(mac_address)
        nodes_dict = {}
        url = f"https://api.macvendors.com/{mac_address}"
        response = requests.get(url)

        nodes_dict.update({mac_address: response.text})

        nodes.append(nodes_dict)
        
    capture.close()

    return nodes

# print(network_nodes("Trace.pcapng"))

"""
UNFINISHED
"""