import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet
import json

@tool
def ip_mac(PCAP: str) -> list:
    """
    Tool to find the all the MAC addresses and their corresponding IP addresses
    """

    # Load the pcapng file
    capture = pyshark.FileCapture(PCAP)

    subnet = None

    mappings = []

    for packet in capture:
        mapping_dict = {}
        if ('eth' in packet and 'ip' in packet):
            mapping_dict.update({packet.eth.src: packet.ip.src})
            if mapping_dict not in mappings:
                mappings.append(mapping_dict)

    seen_keys = set()
    unique_mappings = []

    for d in mappings:
        for key in d:
            if key not in seen_keys:
                seen_keys.add(key)
                unique_mappings.append(d)

    capture.close()

    return json.dumps(unique_mappings)

# print(ip_mac("Trace.pcapng"))

"""
UNFINISHED
"""