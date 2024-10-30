from langchain_core.tools import tool
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

        #list of dicts to represent mac and IP mappings
        mappings = []

        #gather all of the MAC and IP's in every packet in every capture
        for packet in capture:
            mapping_dict = {}
            if (packet.haslayer(Ether) and packet.haslayer(IP)):
                mapping_dict.update({packet[Ether].src: packet[IP].src})
                if mapping_dict not in mappings:
                    mappings.append(mapping_dict)

        key_counter = Counter()

        #count the number of times each mac address shows up (the mac address is the key and IP is the value in every dict in mappings)
        for d in mappings:
            for key in d:
                key_counter[key] += 1

        #whichever is the most common key (mac address) is likely a router
        router_mac = key_counter.most_common(1)[0][0]
        if (router_mac not in routers):
            routers.append(router_mac)

    result = ','.join(routers)

    return result

"""
UNFINISHED
"""