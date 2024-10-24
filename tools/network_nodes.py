import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet
import requests
from dotenv import load_dotenv
import os
import scapy
from scapy.all import rdpcap, IP, Ether
from typing import List

@tool
def network_nodes(PCAPs: List[str]) -> List[str]:
    """
    Tool to find any information about a specific 
    nodes in the network the trace was done on 
    or questions about specific MAC addresses
    or specific devices on the network.
    """

    load_dotenv(dotenv_path="C:/Users/sarta/BigProjects/packto.ai/keys.env")
    mac_key = os.getenv('MACADDRESS_IO_API_KEY')

    nodes = []

    # Load the pcapng file
    for PCAP in PCAPs:
        mac_addresses = []
        capture = rdpcap(PCAP)

        for packet in capture:
            if packet.haslayer(Ether):
                if (packet[Ether].src not in mac_addresses):
                    mac_addresses.append(packet[Ether].src)
                if (packet[Ether].dst not in mac_addresses):
                    mac_addresses.append(packet[Ether].dst)
        
        for mac_address in mac_addresses:
            print(mac_address)
            nodes_dict = {}
            url = f"https://api.macvendors.com/{mac_address}"
            response = requests.get(url)

            nodes_dict.update({mac_address: response.text})

            nodes.append(nodes_dict)

    return nodes

# print(network_nodes(["Trace.pcapng", "Trace2.pcapng"]))

"""
UNFINISHED
"""