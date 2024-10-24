import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet
import json
import scapy
from scapy.all import rdpcap, Ether, IP
from typing import List

@tool
def ip_mac(PCAPs: List[str]) -> list:
    """
    Tool to find the all the MAC addresses and their corresponding IP addresses
    """
    mappings = []
    for PCAP in PCAPs:
        # Load the pcapng file
        capture = rdpcap(PCAP)

        for packet in capture:
            mapping_dict = {}
            if (packet.haslayer(Ether) and packet.haslayer(IP)):
                mapping_dict.update({packet[Ether].src: packet[IP].src})
                if mapping_dict not in mappings:
                    mappings.append(mapping_dict)

    seen_keys = set()
    unique_mappings = []

    for d in mappings:
        for key in d:
            if key not in seen_keys:
                seen_keys.add(key)
                unique_mappings.append(d)


    return json.dumps(unique_mappings)

# print(ip_mac(["Trace.pcapng", "Trace2.pcapng"]))

"""
UNFINISHED
"""