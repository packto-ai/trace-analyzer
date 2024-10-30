from langchain_core.tools import tool
import pyshark.packet
import pyshark.packet.packet
import scapy
from scapy.all import rdpcap

@tool
def analyze_packet(PCAP: str, packetnum: int) -> str:
    """
    Tool to find any information about a specific 
    packet within a trace
    """

    packet_index = packetnum - 1 #For indexing. 5th packet will be at 4th index of capture for example

    # Load the pcapng file
    capture = rdpcap(PCAP)

    #get the packet the user specified
    packet = capture[packet_index]

    packet_show = packet.show(dump=True)

    #include everything from the packet besides the raw hex
    summary = packet_show.split("###[ Raw ]###")[0].rstrip()

    return summary

