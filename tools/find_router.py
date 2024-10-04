import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet
from collections import Counter

@tool
def find_router(PCAP: str) -> str:
    """
    Tool to find what the router on the local subnet is
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

    key_counter = Counter()

    seen_keys = set()
    unique_mappings = []

    for d in mappings:
        for key in d:
            key_counter[key] += 1

    router_mac = key_counter.most_common(1)[0][0]

    capture.close()

    return router_mac

# print(ip_mac("Trace.pcapng"))

"""
UNFINISHED
"""