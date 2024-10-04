import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet

# @tool
def ip_mac(PCAP: str) -> list:
    """
    Tool to find the local subnet where the trace is taken
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

    return unique_mappings

print(ip_mac("Trace.pcapng"))

"""
UNFINISHED
"""