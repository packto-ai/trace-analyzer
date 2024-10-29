import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet
from collections import Counter
from typing import List
import scapy
from scapy.all import rdpcap, IP, Ether

@tool
def find_router(PCAPs: List[str]) -> str:
    """
    Tool to find what the router on the local subnet is
    """
    routers = []

    for PCAP in PCAPs:
        # Load the pcapng file
        capture = rdpcap(PCAP)

        mappings = []

        for packet in capture:
            mapping_dict = {}
            if (packet.haslayer(Ether) and packet.haslayer(IP)):
                mapping_dict.update({packet[Ether].src: packet[IP].src})
                if mapping_dict not in mappings:
                    mappings.append(mapping_dict)

        key_counter = Counter()

        for d in mappings:
            for key in d:
                key_counter[key] += 1

        router_mac = key_counter.most_common(1)[0][0]
        if (router_mac not in routers):
            routers.append(router_mac)

    result = ','.join(routers)

    return result

# print(find_router(["Trace.pcapng", "Trace2.pcapng"]))

"""
UNFINISHED
"""