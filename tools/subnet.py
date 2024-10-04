import pyshark
from langchain_core.tools import tool
import asyncio
import pyshark.packet
import pyshark.packet.packet

# @tool
def network_nodes(PCAP: str) -> str:
    """
    Tool to find the local subnet where the trace is taken
    """

    # Load the pcapng file
    capture = pyshark.FileCapture(PCAP)

    subnet = None
    for packet in capture:
        if packet.highest_layer == "ARP":
            if ('arp' in packet):
                ip = packet.arp.src_proto_ipv4
                ip_parts = ip.split('.')
                ip_parts[-1] = '0'
                subnet = '.'.join(ip_parts)

    return subnet

print(network_nodes("Trace.pcapng"))

